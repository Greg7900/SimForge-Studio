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


class PedalInfo:
    def __init__(self, port):
        self.port = port
        self.tag = None
        self.version = None
        self.fw = None
        self.state = None
        self.config = None
        self.ext = None             # dernier état détaillé (debugFlags0 bit 64), pour le diagnostic du servo
        self.ext_vmax = 0.0         # tension du servo la plus haute vue depuis la dernière remise à zéro (V)
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
    def __init__(self, port, baud):
        s = serial.Serial()
        s.port = port
        s.baudrate = baud
        s.timeout = 0.02
        s.write_timeout = 0.5
        s.dtr = False          # DTR/RTS au repos : sinon le circuit d'auto-reset redémarre l'ESP32
        s.rts = False
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
                          brakeResistorState_b=1 if self._v > 40 else 0)
                self.out += PP.frame(PP.T_STATE_EXT, PP._pack(PP.STATE_EXT_FIELDS, PP.STATE_EXT_S, ex), tag=self.tag)
        b = bytes(self.out)
        self.out.clear()
        return b

    def write(self, b):
        for f in self.parser.feed(b):
            if f.ptype == PP.T_ACTION:
                a = PP._unpack(PP.ACTION_FIELDS, PP.ACTION_S, f.raw[6:-4])
                if a["returnPedalConfig_u8"]:
                    self.out += PP.build_config(self.cfg, tag=self.tag)
                if a["systemAction_u8"] == PP.ACT_BEEP:
                    self.out += b"beep\r\n"
                if a["systemAction_u8"] == PP.ACT_RESTART:
                    self.out += b"ESP restart by user request\r\nSetup end\r\n"
            elif f.ptype == PP.T_CONFIG and f.data:
                if not PP.plausible(f.data):
                    self.cfg = dict(f.data)
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
                            v = fr.data["pedalFirmwareVersion_au8"]
                            info.fw = f"{v[0]}.{v[1]:02d}.{v[2]:02d}"          # ex. 26.43.07
                            n_states += 1
                            with mgr.lock:
                                mgr.buf.append((info.port, now, fr.data))
                            if not self.ok:
                                self.ok = True
                                mgr._probe_done(self, True)
                        elif fr.ptype == PP.T_STATE_EXT and fr.data:
                            info.ext = fr.data
                            info.ext_vmax = max(info.ext_vmax, fr.data["servoVoltage0p1V_i16"] / 10)
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
                if self.ok and not asked and not info.incompatible:
                    asked = True
                    dev.write(PP.build_action(tag=info.tag or 0, systemAction_u8=PP.ACT_WAKEUP))
                    time.sleep(0.02)
                    dev.write(PP.build_action(tag=info.tag or 0, returnPedalConfig_u8=1))
                if self.ok and now - info.last_rx > 3.0:
                    mgr.log.emit("warn", T("Pédale {p} : plus de données").format(p=info.port))
                    break
                while True:
                    try:
                        data, what = self.q.get_nowait()
                    except queue.Empty:
                        break
                    dev.write(data)
                    if what:
                        mgr.log.emit("info", f"→ {info.name} : {what}")
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

    def _baud(self, port):
        if self.demo or serial is None:
            return PP.BAUD
        for p in serial.tools.list_ports.comports():
            if p.device == port and p.vid == ESPRESSIF_VID:
                return 921600               # USB CDC natif : vitesse ignorée, le plugin utilise 921600
        return PP.BAUD

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
                baud = self._baud(port)
                opener = (lambda p=port, b=baud: SerialPort(p, b))
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

    def send_config(self, port, cfg: dict, store: bool):
        l = self.links.get(port)
        if not l:
            return T("pédale non connectée")
        errs = PP.plausible(cfg)
        if errs:
            return "; ".join(errs)
        c = dict(cfg)
        l.send(PP.build_config(c, store=store, tag=l.info.tag or 0),
               T("configuration mémorisée") if store else T("configuration appliquée"))
        # relecture pour confirmer ce que la pédale a retenu
        QTimer.singleShot(400, lambda: self.request_config(port))
        return ""

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
