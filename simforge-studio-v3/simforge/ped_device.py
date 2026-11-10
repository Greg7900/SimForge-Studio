"""
Liaison avec les pédales actives ChrGri (une pédale = un port série USB).

Un thread par port ouvert : il lit en continu les trames d'état (envoyées par la pédale), récupère la
configuration à la demande, et envoie configurations et actions. Un thread de recherche teste les ports série
de type ESP32 qui ne sont pas encore ouverts. L'IHM reçoit les états à 30 Hz au plus (minuterie dans le thread IHM).
"""
from __future__ import annotations

import collections
import math
import queue
import random
import threading
import time

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from . import ped_protocol as PP
from .i18n import T

try:
    import serial
    import serial.tools.list_ports
except Exception:  # pragma: no cover
    serial = None

# ponts USB-série vus sur les cartes ESP32-S3 des pédales (CH343, CH340, CP210x) et USB natif Espressif
CANDIDATE_VIDPID = {(0x1A86, 0x55D3), (0x1A86, 0x7523), (0x1A86, 0x55D4), (0x10C4, 0xEA60)}
ESPRESSIF_VID = 0x303A
EXCLUDE_VIDPID = {(0x1209, 0x0D40)}      # Odrive-Wheel


def new_ext_acc():
    """Cumuls sur les états détaillés : nombre, trames « en oscillation », force brute (kg) et sa somme des carrés."""
    return {"n": 0, "osc": 0, "r": 0.0, "rr": 0.0}


class FakeBridgePort:
    """Récepteur sans fil simulé : répond seulement aux trames d'appairage."""
    table = ([bytes(6)] * 4, 11)                 # gardée entre deux ouvertures, comme l'EEPROM
    own_mac = bytes((0x34, 0x85, 0x18, 0xBB, 0x00, 0x03))

    def __init__(self):
        self.parser = PP.Parser()
        self.out = bytearray(b"[L]Bridge ready\r\n")

    def read(self):
        time.sleep(0.005)
        b = bytes(self.out)
        self.out.clear()
        return b

    def write(self, b):
        for f in self.parser.feed(b):
            if f.ptype == PP.T_MAC:
                if f.store and f.data:
                    FakeBridgePort.table = (list(f.data["macs"]), f.data["channel"])
                macs, ch = FakeBridgePort.table
                payload = PP.MAC_S.pack(*[1 if any(m) else 0 for m in macs], b"".join(macs), self.own_mac,
                                        PP.N_BRIDGE, ch)
                self.out += PP.frame(PP.T_MAC, payload, 0, 0, PP.MAC_VERSION)

    def close(self):
        pass


class PedalInfo:
    def __init__(self, port):
        self.port = port
        self.tag = None
        self.version = None
        self.fw = None
        self.fw_v = None            # version brute (3 nombres)
        self.mac = None             # dernière table d'appairage reçue (PP.unpack_mac)
        self.state = None
        self.config = None
        self.ext = None             # dernier état détaillé (debugFlags0 bit 64), pour le diagnostic du servo
        self.ext_vmax = 0.0         # tension du servo la plus haute vue depuis la dernière remise à zéro (V)
        self.ext_acc = new_ext_acc()  # cumuls de l'auto-test (remis à zéro par lui)
        self.rate = 0.0
        self.incompatible = False
        self.last_rx = 0.0
        self.board = None
        self.bad_crc = 0

    @property
    def name(self):
        if self.tag is None:
            return self.port
        return f"{PP.PEDAL_NAMES.get(self.tag, '?')} ({self.port})"


# ======================================================================
#  Port réel / pédale simulée
# ======================================================================
class SerialPort:
    def __init__(self, port, baud, native=False):
        s = serial.Serial()
        s.port = port
        s.baudrate = baud
        s.timeout = 0.02
        s.write_timeout = 0.5
        # puce série (CH343…) : DTR/RTS au repos, sinon le circuit d'auto-reset redémarre l'ESP32.
        # USB natif (firmware « un câble ») : DTR et RTS levés, sinon le firmware n'envoie rien (USBCDC d'Arduino ne
        # se dit « connecté » qu'avec les deux) ; pas de reset possible par DTR/RTS, il est désactivé dans le firmware
        s.dtr = native
        s.rts = native
        s.open()
        self.s = s

    def read(self):
        n = self.s.in_waiting
        return self.s.read(n or 1)

    def write(self, b):
        self.s.write(b)

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


class FakePedalPort:
    """Pédale simulée : répond comme le firmware (états à ~100 Hz, configuration sur demande)."""

    def __init__(self, tag):
        self.tag = tag
        self.own_mac = bytes((0x34, 0x85, 0x18, 0xAA, 0x00, tag))
        self.mac_table = ([bytes(6)] * 4, 11)
        self.cfg = PP.default_config()
        self.cfg["pedalType_u8"] = tag
        self.out = bytearray()
        self.t0 = time.perf_counter()
        self.next = self.t0
        self.parser = PP.Parser()
        self.out += b"[L]: Pedal booted\r\n"

    def read(self):
        now = time.perf_counter()
        time.sleep(0.005)
        while now >= self.next:
            self.next += 0.01
            t = self.next - self.t0
            press = max(0.0, math.sin(t * (0.8 + 0.3 * self.tag)) * 1.1)
            pos = min(1.0, press)
            st = {n: (0 if c == 1 else [0] * c) for n, _t, c in PP.STATE_BASIC_FIELDS}
            st.update(pedalPosition_u16=int(pos * 65535), pedalForce_u16=int(min(1.0, pos ** 1.6) * 65535),
                      joystickOutput_u16=int(min(1.0, pos ** 1.6) * 65535 * self.cfg["maxGameOutput_u8"] / 100),
                      pedalFirmwareVersion_au8=[26, 43, 7], servoStatus_u8=1)
            self.out += PP.frame(PP.T_STATE, PP._pack(PP.STATE_BASIC_FIELDS, PP.STATE_S, st), tag=self.tag)
            if self.cfg["debugFlags0_u8"] & 64:
                vel = (pos - getattr(self, "_pos", pos)) / 0.01
                self._pos = pos
                self._v = max(36.0, getattr(self, "_v", 36.0) * 0.995 + 0.18 * max(0.0, -vel))
                ex = {n: (0 if c == 1 else [0] * c) for n, _t, c in PP.STATE_EXT_FIELDS}
                ex.update(servoVoltage0p1V_i16=int(self._v * 10), servoCurrentPercent_i16=int(pos * 60),
                          servoPositionError_i16=int(vel * 3), servoVelocityRpm_i16=int(vel * 300),
                          brakeResistorState_b=1 if self._v > 40 else 0,
                          pedalForceRaw_fl32=pos * 60 + random.gauss(0, 0.3),
                          pedalForceFiltered_fl32=pos * 60,
                          admittance_isOscillating=1 if (self.cfg["kfModelNoise_u8"] > 140
                                                         and self.cfg["virtualPedalDampingInPercent_u8"] < 150
                                                         and abs(vel) > 0.05 and random.random() < 0.3) else 0)
                self.out += PP.frame(PP.T_STATE_EXT, PP._pack(PP.STATE_EXT_FIELDS, PP.STATE_EXT_S, ex), tag=self.tag)
        b = bytes(self.out)
        self.out.clear()
        return b

    def _mac_reply(self, f, node):
        if f.store and f.data:
            self.mac_table = (list(f.data["macs"]), f.data["channel"])
            self.out += b"[MAC] Stored & Applied MAC Addresses table via Serial COM.\r\n"
        macs, ch = self.mac_table
        payload = PP.MAC_S.pack(*[1 if any(m) else 0 for m in macs], b"".join(macs), self.own_mac, node, ch)
        self.out += PP.frame(PP.T_MAC, payload, 0, node, PP.MAC_VERSION)

    def write(self, b):
        for f in self.parser.feed(b):
            if f.ptype == PP.T_MAC:
                self._mac_reply(f, self.tag)
                continue
            if f.ptype == PP.T_ACTION:
                a = PP._unpack(PP.ACTION_FIELDS, PP.ACTION_S, f.raw[6:-4])
                if a["returnPedalConfig_u8"]:
                    self.out += PP.build_config(self.cfg, tag=self.tag)
                if a["systemAction_u8"] == PP.ACT_RESTART:
                    self.out += b"ESP restart by user request\r\nSetup end\r\n"
            elif f.ptype == PP.T_CONFIG and f.data:
                if not PP.plausible(f.data):
                    self.cfg = dict(f.data)
                    if self.cfg["debugFlags0_u8"] & PP.DBG_CLEAR_ALARMS:
                        self.cfg["debugFlags0_u8"] &= ~PP.DBG_CLEAR_ALARMS & 0xFF
                        self.out += (b"Set clear alarm history flag\r\nClearing all servo alarms.\r\n\r\n"
                                     b"iSV57 alarm history: Alarm Idx: 0,    Alarm Code: C0 --> Overvoltage\n\r\n\r\n")
                    # comme le firmware : une pédale assignée garde son rôle, sauf configuration enregistrée
                    if f.store or self.tag > 2:
                        self.tag = self.cfg["pedalType_u8"]
                    else:
                        self.cfg["pedalType_u8"] = self.tag
                    self.out += b"Updating pedal config from serial\r\n"
                    if f.store:
                        self.out += b"config stored to EEPROM\r\n"
                else:
                    self.out += b"Implausible config\r\n"

    def close(self):
        pass


# ======================================================================
#  Thread d'un port
# ======================================================================
class PedalLink(QThread):
    def __init__(self, mgr, port, opener):
        super().__init__()
        self.mgr = mgr
        self.info = PedalInfo(port)
        self.opener = opener
        self.q: queue.Queue = queue.Queue()
        self._run = True
        self.parser = PP.Parser()
        self.ok = False

    def send(self, data: bytes, what=""):
        self.q.put((data, what))

    def stop(self):
        self._run = False

    def run(self):
        info, mgr = self.info, self.mgr
        try:
            dev = self.opener()
        except Exception as e:
            mgr.log.emit("debug", f"{info.port}: {e}")
            mgr._probe_done(self, False)
            return
        t_open = time.perf_counter()
        n_states, t_rate = 0, t_open
        asked = False
        try:
            while self._run:
                try:
                    data = dev.read()
                except Exception as e:
                    mgr.log.emit("warn", T("Pédale {p} : port perdu ({e})").format(p=info.port, e=e))
                    break
                now = time.perf_counter()
                if data:
                    for fr in self.parser.feed(data):
                        info.last_rx = now
                        if fr.ptype == PP.T_MAC:            # sa propre version de trame : avant le contrôle de version
                            if fr.data:
                                info.mac = fr.data
                                mgr.mac_read.emit(info.port, dict(fr.data))
                            continue
                        info.version = fr.version
                        if fr.version != PP.VERSION:
                            if not info.incompatible:
                                info.incompatible = True
                                info.tag = fr.tag
                                self.ok = True
                                mgr._probe_done(self, True)
                                mgr.log.emit("warn", T("Pédale {p} : firmware incompatible (structure v{v}, SimForge "
                                                       "attend v{w}). Flashe le firmware fourni (onglet Firmware des "
                                                       "pédales).").format(p=info.port, v=fr.version, w=PP.VERSION))
                            continue
                        if fr.ptype == PP.T_STATE:
                            info.state = fr.data
                            info.tag = fr.tag
                            info.fw_v = tuple(fr.data["pedalFirmwareVersion_au8"])
                            info.fw = PP.fw_text(info.fw_v)          # ex. 26.43.07, ou 26.43.07 SimForge
                            n_states += 1
                            with mgr.lock:
                                mgr.buf.append((info.port, now, fr.data))
                            if not self.ok:
                                self.ok = True
                                mgr._probe_done(self, True)
                        elif fr.ptype == PP.T_STATE_EXT and fr.data:
                            info.ext = fr.data
                            info.ext_vmax = max(info.ext_vmax, fr.data["servoVoltage0p1V_i16"] / 10)
                            a, raw = info.ext_acc, fr.data["pedalForceRaw_fl32"]
                            a["n"] += 1
                            a["osc"] += 1 if fr.data["admittance_isOscillating"] else 0
                            a["r"] += raw
                            a["rr"] += raw * raw
                        elif fr.ptype == PP.T_CONFIG:
                            info.config = fr.data
                            mgr.config_read.emit(info.port, dict(fr.data))
                    info.bad_crc = self.parser.bad_crc
                    for line in self.parser.lines:
                        mgr.text.emit(info.port, line)
                        # la pédale a redémarré sans que le port se ferme (puce série USB) : on la réveille à nouveau
                        # (sinon, réglée sur « attend le logiciel », elle reste en veille) et on relit sa configuration
                        if "Setup end" in line or "Pedal in STANDBY" in line:
                            asked = False
                    self.parser.lines.clear()
                if now - t_rate >= 1.0:
                    info.rate = n_states / (now - t_rate)
                    n_states, t_rate = 0, now
                if not self.ok and now - t_open > 2.0:
                    break                                   # pas une pédale
                if self.ok and now - info.last_rx > 3.0:
                    mgr.log.emit("warn", T("Pédale {p} : plus de données").format(p=info.port))
                    break
                try:
                    if self.ok and not asked and not info.incompatible:
                        asked = True
                        dev.write(PP.build_action(tag=info.tag or 0, systemAction_u8=PP.ACT_WAKEUP))
                        time.sleep(0.02)
                        dev.write(PP.build_action(tag=info.tag or 0, returnPedalConfig_u8=1))
                    while True:
                        try:
                            data, what = self.q.get_nowait()
                        except queue.Empty:
                            break
                        dev.write(data)
                        if what:
                            mgr.log.emit("info", f"→ {info.name} : {what}")
                except Exception as e:
                    # port perdu en cours d'envoi : on le dit (une trame « mémoriser » a pu ne pas partir)
                    mgr.log.emit("warn", T("Pédale {p} : envoi impossible, port perdu ({e})").format(p=info.port, e=e))
                    break
        finally:
            dev.close()
            if self.ok:
                mgr._lost(self)
            else:
                mgr._probe_done(self, False)


class PedalManager(QObject):
    changed = Signal()                       # liste des pédales modifiée
    states = Signal(list)                    # [(port, t, état)]
    config_read = Signal(str, dict)
    text = Signal(str, str)                  # (port, ligne texte du firmware)
    mac_read = Signal(str, dict)             # (port, table d'appairage sans fil)
    log = Signal(str, str)
    _probe_sig = Signal(object, bool)        # interne : résultats des threads ramenés dans le thread IHM
    _lost_sig = Signal(object)

    def __init__(self, demo=False, parent=None):
        super().__init__(parent)
        self._probe_sig.connect(self._on_probe)
        self._lost_sig.connect(self._on_lost)
        self.demo = demo
        self.links: dict[str, PedalLink] = {}
        self.probing: dict[str, PedalLink] = {}
        self.blocked: dict[str, float] = {}      # port → instant jusqu'auquel ne pas tester
        self.paused: set[str] = set()            # ports réservés (flashage)
        self.lock = threading.Lock()
        self.buf: collections.deque = collections.deque(maxlen=5000)
        self._scan = QTimer(self)
        self._scan.setInterval(2000)
        self._scan.timeout.connect(self.scan)
        self._pump = QTimer(self)
        self._pump.setInterval(33)
        self._pump.timeout.connect(self._pump_states)
        self.enabled = True

    def start(self):
        self._scan.start()
        self._pump.start()
        QTimer.singleShot(300, self.scan)

    def stop(self):
        self._scan.stop()
        for l in list(self.links.values()) + list(self.probing.values()):
            l.stop()
        for l in list(self.links.values()) + list(self.probing.values()):
            l.wait(800)

    # ------------------------------------------------------------ recherche
    def candidates(self):
        if self.demo:
            return ["DEMO-FREIN", "DEMO-ACCEL"]
        if serial is None:
            return []
        out = []
        for p in serial.tools.list_ports.comports():
            if p.vid is None:
                continue
            if (p.vid, p.pid) in EXCLUDE_VIDPID:
                continue
            if (p.vid, p.pid) in CANDIDATE_VIDPID or p.vid == ESPRESSIF_VID:
                out.append(p.device)
        return out

    def _native(self, port):
        """Port USB natif de l'ESP32-S3 (firmware « un câble ») plutôt que puce série."""
        if self.demo or serial is None:
            return False
        return any(p.device == port and p.vid == ESPRESSIF_VID for p in serial.tools.list_ports.comports())

    def scan(self):
        if not self.enabled:
            return
        now = time.perf_counter()
        for port in self.candidates():
            if port in self.links or port in self.probing or port in self.paused:
                continue
            if self.blocked.get(port, 0) > now:
                continue
            if self.demo:
                tag = 1 if "FREIN" in port else 2
                opener = (lambda t=tag: FakePedalPort(t))
            else:
                # USB natif : vitesse ignorée (921600 comme le plugin ; surtout pas 1200 = mode flashage)
                native = self._native(port)
                opener = (lambda p=port, n=native: SerialPort(p, 921600 if n else PP.BAUD, n))
            l = PedalLink(self, port, opener)
            self.probing[port] = l
            l.start()

    def _probe_done(self, link, ok):
        self._probe_sig.emit(link, ok)

    def _lost(self, link):
        self._lost_sig.emit(link)

    def _on_probe(self, link, ok):
        port = link.info.port
        if self.probing.get(port) is link:
            del self.probing[port]
        if ok:
            self.links[port] = link
            self.log.emit("info", T("Pédale trouvée : {n}").format(n=link.info.name))
            self.changed.emit()
        else:
            self.blocked[port] = time.perf_counter() + 10.0

    def _on_lost(self, link):
        port = link.info.port
        if self.links.get(port) is link:
            del self.links[port]
            self.blocked[port] = time.perf_counter() + 2.0
            self.log.emit("warn", T("Pédale déconnectée : {n}").format(n=link.info.name))
            self.changed.emit()

    def _pump_states(self):
        with self.lock:
            if not self.buf:
                return
            batch = list(self.buf)
            self.buf.clear()
        self.states.emit(batch)

    # ------------------------------------------------------------ API
    def pedals(self) -> list[PedalInfo]:
        return [l.info for l in sorted(self.links.values(), key=lambda l: (l.info.tag if l.info.tag is not None
                                                                           else 9, l.info.port))]

    def info(self, port):
        l = self.links.get(port)
        return l.info if l else None

    def request_config(self, port):
        l = self.links.get(port)
        if l:
            l.send(PP.build_action(tag=l.info.tag or 0, returnPedalConfig_u8=1))

    def send_config(self, port, cfg: dict, store: bool, clear_alarms=False, reread=True):
        l = self.links.get(port)
        if not l:
            return T("pédale non connectée")
        errs = PP.plausible(cfg)
        if errs:
            return "; ".join(errs)
        c = dict(cfg)
        # le bit « effacer les alarmes » ne part qu'avec la commande dédiée : enregistré, il figerait la pédale 1 s
        # à chaque démarrage et à chaque réglage
        c["debugFlags0_u8"] &= ~PP.DBG_CLEAR_ALARMS & 0xFF
        if clear_alarms:
            c["debugFlags0_u8"] |= PP.DBG_CLEAR_ALARMS
            what = T("lecture et effacement des alarmes du servo")
        else:
            what = T("configuration mémorisée") if store else T("configuration appliquée")
        l.send(PP.build_config(c, store=store, tag=l.info.tag or 0), what)
        # relecture pour confirmer ce que la pédale a retenu (l'effacement des alarmes la fige 1 s)
        if reread:
            QTimer.singleShot(1600 if clear_alarms else 400, lambda: self.request_config(port))
        return ""

    def bridge_ports(self):
        """Ports série qui ne sont pas une pédale connectée : candidats pour le récepteur (sa prise UART)."""
        if self.demo:
            return ["DEMO-RECEPTEUR"]
        if serial is None:
            return []
        return [p.device for p in serial.tools.list_ports.comports()
                if p.vid is not None and (p.vid, p.pid) in CANDIDATE_VIDPID and p.device not in self.links]

    def bridge_exchange(self, port, frame_bytes, wait=6.0):
        """Ouvre le port du récepteur le temps d'un échange : envoie la trame, renvoie (table reçue ou None, erreur).
        Bloquant (≈ wait s) : à lancer hors du thread de l'interface."""
        self.paused.add(port)
        l = self.probing.get(port)
        if l:
            l.stop()
            l.wait(800)
        dev = None
        try:
            dev = FakeBridgePort() if self.demo else SerialPort(port, PP.BAUD)
            parser, got, n_rx, last = PP.Parser(), None, 0, ""
            t_end = time.perf_counter() + wait
            t_send = 0.0
            while time.perf_counter() < t_end and got is None:
                # renvoyée toutes les 0,5 s : ouvrir le port peut redémarrer l'ESP32 (circuit d'auto-reset de la
                # puce série), qui met quelques secondes à écouter
                if time.perf_counter() - t_send > 0.5:
                    dev.write(frame_bytes)
                    t_send = time.perf_counter()
                data = dev.read() or b""
                n_rx += len(data)
                for fr in parser.feed(data):
                    if fr.ptype == PP.T_MAC and fr.data:
                        got = fr.data
                if parser.lines:
                    last = parser.lines[-1]
                    parser.lines.clear()
            if got:
                return got, ""
            # ce qui a été reçu aide à comprendre : rien = mauvais port ou prise ; du texte = autre firmware
            return None, (T("pas de réponse") + " ; " + (T("rien reçu") if not n_rx else
                          T("{n} octets reçus, dernier message : « {m} »").format(n=n_rx, m=last[:80] or "?")))
        except Exception as e:
            return None, str(e)
        finally:
            if dev:
                dev.close()
            self.paused.discard(port)

    def boot_log(self, port, seconds=3.0):
        """Redémarre l'ESP32 par la puce série (RTS = broche EN) et renvoie ce qu'il écrit au démarrage, lu à
        115200 bauds : le programme d'amorçage de la puce y dit pourquoi un firmware ne démarre pas. Bloquant."""
        if self.demo:
            return "ESP-ROM:esp32s3-20210327\nrst:0x1 (POWERON),boot:0x8 (SPI_FAST_FLASH_BOOT)\nentry 0x403c98d0", ""
        self.paused.add(port)
        l = self.probing.get(port)
        if l:
            l.stop()
            l.wait(800)
        s = None
        try:
            s = serial.Serial()
            s.port, s.baudrate, s.timeout = port, 115200, 0.05
            s.dtr = False
            s.rts = False
            s.open()
            s.rts = True                # EN à 0 : reset
            time.sleep(0.15)
            s.reset_input_buffer()
            s.rts = False
            buf = bytearray()
            t_end = time.perf_counter() + seconds
            while time.perf_counter() < t_end:
                buf += s.read(4096)
            text = buf.translate(None, PP._NOT_TEXT).decode("ascii", "replace")
            return "\n".join(ln.rstrip() for ln in text.splitlines() if ln.strip()), ""
        except Exception as e:
            return "", str(e)
        finally:
            if s:
                try:
                    s.close()
                except Exception:
                    pass
            self.paused.discard(port)

    def send_mac(self, port, macs=None, channel=11, store=False):
        """Sans fil : demande la table d'appairage de la pédale (store=False) ou lui en enregistre une."""
        l = self.links.get(port)
        if l:
            l.send(PP.build_mac(macs, channel, store), T("table d'appairage sans fil enregistrée") if store else "")

    def action(self, port, what="", **kw):
        l = self.links.get(port)
        if l:
            l.send(PP.build_action(tag=l.info.tag or 0, **kw), what)

    def release(self, port):
        """Ferme le port (avant flashage) et ne le reteste plus tant qu'il est réservé."""
        self.paused.add(port)
        for d in (self.links, self.probing):
            l = d.get(port)
            if l:
                l.stop()
                l.wait(1500)

    def unpause(self, port):
        self.paused.discard(port)
        self.blocked.pop(port, None)
