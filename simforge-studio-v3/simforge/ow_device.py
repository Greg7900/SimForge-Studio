"""
Liaison avec la carte Odrive-Wheel.

Deux threads :
  • SerialThread : port série (réglages, commandes, console). File de travaux + file urgente (STOP).
  • HidThread    : rapport HID à 1 kHz (télémétrie), surveillance de survitesse, maintien du STOP.

L'IHM ne parle qu'à l'objet Board (méthodes thread-safe + signaux Qt).
Le STOP met l'axe au repos (IDLE) : le moteur n'est plus alimenté, rien n'est mémorisé dans la carte.
"""
from __future__ import annotations

import collections
import math
import queue
import random
import re
import threading
import time
import traceback

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from . import ow_protocol as P
from .i18n import T

try:
    import hid  # paquet pip « hidapi »
except Exception:  # pragma: no cover
    hid = None
try:
    import serial
    import serial.tools.list_ports
except Exception:  # pragma: no cover
    serial = None


class LinkLost(Exception):
    pass


# ======================================================================
#  Port série réel
# ======================================================================
class SerialLink:
    name = "USB"

    def __init__(self, port: str):
        self.port = port
        try:
            self.s = serial.Serial()
            self.s.port = port
            self.s.baudrate = 115200
            self.s.timeout = 0.02
            self.s.write_timeout = 0.5
            self.s.dtr = True     # TinyUSB ignore les octets tant que DTR est bas
            self.s.rts = True
            self.s.open()
        except Exception as e:
            raise LinkLost(str(e))
        time.sleep(0.05)
        self.buf = b""
        self._flush()

    @staticmethod
    def find() -> str | None:
        if serial is None:
            return None
        for p in serial.tools.list_ports.comports():
            if p.vid == P.VID and p.pid == P.PID:
                return p.device
        return None

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass

    # ------------------------------------------------------------ bas niveau
    def _flush(self):
        try:
            self.s.reset_input_buffer()
        except Exception as e:
            raise LinkLost(str(e))
        self.buf = b""

    def _send(self, text: str):
        self._flush()
        try:
            self.s.write(text.encode("ascii", "replace"))
        except Exception as e:
            raise LinkLost(str(e))

    def _fill(self):
        try:
            n = self.s.in_waiting
            chunk = self.s.read(n or 1)
        except Exception as e:
            raise LinkLost(str(e))
        if chunk:
            self.buf += chunk
        return bool(chunk)

    def _line(self, deadline: float) -> str | None:
        while True:
            if b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                s = line.decode("ascii", "replace").strip("\r ")
                if s:
                    return s
                continue
            if time.perf_counter() > deadline:
                return None
            self._fill()

    # ------------------------------------------------------------ commandes
    def offb(self, cmd: str, timeout: float = 0.8) -> str | None:
        """Commande OpenFFBoard ; renvoie la valeur entre « | » et « ] » (réponse multi-lignes possible)."""
        self._send(cmd + "\n")
        head = re.split(r"[?=!]", cmd, 1)[0]
        deadline = time.perf_counter() + timeout
        parts = None
        while True:
            line = self._line(deadline)
            if line is None:
                return None
            if parts is None:
                if not line.startswith("[" + head):
                    continue                       # ligne parasite
                parts = [line]
            else:
                parts.append(line)
            if parts[-1].endswith("]"):
                txt = "\n".join(parts)
                i = txt.find("|")
                return txt[i + 1:-1] if i >= 0 else None

    def r(self, path: str, timeout: float = 0.5) -> str | None:
        self._send(f"r {path}\n")
        return self._line(time.perf_counter() + timeout)

    def w(self, path: str, value: str, timeout: float = 0.5):
        """Écrit puis relit. -> (ok, relu_ou_message).

        L'écriture ODrive est muette si elle réussit. On attend un court instant une éventuelle erreur AVANT
        d'envoyer la relecture : deux réponses consécutives peuvent bloquer la sortie série du firmware
        (commentaire d'ascii_protocol.cpp)."""
        self._send(f"w {path} {value}\n")
        err = self._line(time.perf_counter() + 0.06)
        if err is not None:
            return False, err
        self._send(f"r {path}\n")
        back = self._line(time.perf_counter() + timeout)
        if back is None:
            return False, T("pas de réponse")
        if back in P.ASCII_ERRORS:
            return False, back
        return True, back

    def system(self, cmd: str):
        self._send(cmd + "\n")

    def raw(self, line: str, idle: float = 0.25, total: float = 2.0) -> list[str]:
        self._send(line + "\n")
        out, t_end = [], time.perf_counter() + total
        last = time.perf_counter()
        while time.perf_counter() < t_end:
            got = self._fill() if b"\n" not in self.buf else True
            while b"\n" in self.buf:
                l, self.buf = self.buf.split(b"\n", 1)
                s = l.decode("ascii", "replace").rstrip("\r")
                if s.strip():
                    out.append(s)
                last = time.perf_counter()
            if not got and time.perf_counter() - last > idle:
                break
        if self.buf.strip():
            out.append(self.buf.decode("ascii", "replace").strip())
            self.buf = b""
        return out


# ======================================================================
#  Carte simulée (--demo) : même interface que SerialLink + source HID
# ======================================================================
class FakeDevice:
    """Odrive-Wheel simulée : réglages, machine d'états ODrive, calibrations et un volant qui bouge."""

    def __init__(self):
        self.lock = threading.Lock()
        self.v = {
            "axis.range": "900", "axis.maxtorque": "3.00", "axis.fxratio": "0.80", "axis.invert": "0",
            "axis.ffbinvert": "0", "axis.idlespring": "30", "axis.axisdamper": "0", "axis.axisfriction": "0",
            "axis.axisinertia": "0", "axis.esgain": "120", "axis.esdamp": "15", "axis.maxtorquerate": "0",
            "axis.expo": "0", "axis.exposcale": "100", "axis.zeroofs": "0.000",
            "fx.master": "255", "fx.spring": "64", "fx.damper": "64", "fx.friction": "254", "fx.inertia": "127",
            "fx.filterCfFreq": "120", "fx.filterCfQ": "70", "fx.filterFrFreq": "50", "fx.filterFrQ": "20",
            "fx.filterDaFreq": "30", "fx.filterDaQ": "40", "fx.filterInFreq": "15", "fx.filterInQ": "20",
            "axis.eqweight": "0.0", "axis.eqchassis": "0.0", "axis.eqroad": "0.0",
            "axis.eqweightfreq": "5.00", "axis.eqchassisfreq": "12.00", "axis.eqroadfreq": "25.00",
            "axis.eqweightq": "0.70", "axis.eqchassisq": "1.00", "axis.eqroadq": "0.70",
            "axis.gpiofilt": "0", "axis.gpiofiltf": "60.00", "axis.gpioautocal": "0",
            "sys.vbusdiv": "19", "sys.hwtype": "ODrive-Wheel", "sys.uid": "0039002A3438510B32313537",
            "axis0.motor.config.motor_type": "0", "axis0.motor.config.pole_pairs": "15",
            "axis0.motor.config.torque_constant": "0.516875", "axis0.motor.config.current_lim": "10.000000",
            "axis0.motor.config.current_lim_margin": "8.000000",
            "axis0.motor.config.requested_current_range": "60.000000",
            "axis0.motor.config.current_control_bandwidth": "1000.0000",
            "axis0.motor.config.calibration_current": "5.000000",
            "axis0.motor.config.resistance_calib_max_voltage": "4.000000",
            "axis0.motor.config.phase_resistance": "0.000000", "axis0.motor.config.phase_inductance": "0.000000",
            "axis0.motor.config.pre_calibrated": "0",
            "axis0.motor.fet_thermistor.config.enabled": "1",
            "axis0.motor.fet_thermistor.config.temp_limit_lower": "100.00000",
            "axis0.motor.fet_thermistor.config.temp_limit_upper": "120.00000",
            "axis0.encoder.config.mode": "0", "axis0.encoder.config.cpr": "45000",
            "axis0.encoder.config.use_index": "0", "axis0.encoder.config.direction": "0",
            "axis0.encoder.config.pre_calibrated": "0", "axis0.encoder.config.bandwidth": "1000.0000",
            "axis0.encoder.config.calib_range": "0.020000",
            "axis0.controller.config.control_mode": "1", "axis0.controller.config.input_mode": "1",
            "axis0.controller.config.vel_limit": "8.000000", "axis0.controller.config.vel_limit_tolerance": "1.200000",
            "axis0.controller.config.enable_torque_mode_vel_limit": "1",
            "axis0.controller.config.enable_overspeed_error": "1",
            "axis0.controller.config.vel_gain": "0.166667",
            "axis0.config.startup_motor_calibration": "0", "axis0.config.startup_encoder_index_search": "0",
            "axis0.config.startup_encoder_offset_calibration": "0", "axis0.config.startup_closed_loop_control": "0",
            "config.dc_bus_overvoltage_trip_level": "46.000000", "config.dc_bus_undervoltage_trip_level": "32.000000",
            "config.dc_max_positive_current": "10.000000", "config.dc_max_negative_current": "-2.000000",
            "config.max_regen_current": "0.000000", "config.enable_brake_resistor": "1",
            "config.brake_resistance": "2.000000",
            "hw_version_major": "3", "hw_version_minor": "6", "hw_version_variant": "56",
            "fw_version_major": "0", "fw_version_minor": "5", "fw_version_revision": "6",
            "serial_number": "3365384A3233",
        }
        for pin in P.GPIO_PINS:
            for n, d in (("mode", "0"), ("idx", str(pin - 1)), ("invert", "0"), ("amin", "0"), ("amax", "4095")):
                self.v[f"gpio.{pin}.{n}"] = d
        self.ram = dict(self.v)          # ce qui serait en flash
        self.state, self.req_t, self.req = 1, 0.0, None
        self.motor_cal = False
        self.enc_ready = False
        self.index_found = False
        self.errs = {"axis": 0, "motor": 0, "encoder": 0, "controller": 0, "system": 0}
        self.pos = 0.0          # tours moteur
        self.vel = 0.0
        self.t0 = time.perf_counter()
        self.last = self.t0
        self.online_at = 0.0    # après redémarrage
        self.dfu = False
        self.booting = False
        self.chain = False
        self.torque = self.iq = 0.0
        self.temp = 31.0

    # ------------------------------------------------------------ outils
    def f(self, k, d=0.0):
        try:
            return float(self.v.get(k, d))
        except ValueError:
            return d

    def online(self):
        return not self.dfu and time.perf_counter() >= self.online_at

    def reboot(self, delay=1.6):
        self.v = dict(self.ram)
        self.state, self.req = 1, None
        self.motor_cal = self.v["axis0.motor.config.pre_calibrated"] == "1"
        self.enc_ready = False
        self.index_found = False
        self.errs = {k: 0 for k in self.errs}
        self.online_at = time.perf_counter() + delay
        self.booting = True

    def _boot_sequence(self):
        self.booting = False
        self.chain = True
        if self.v["axis0.config.startup_motor_calibration"] == "1":
            self.request(4)
        elif self.v["axis0.config.startup_encoder_index_search"] == "1":
            self.request(6)
        elif self.v["axis0.config.startup_encoder_offset_calibration"] == "1":
            self.request(7)
        elif self.v["axis0.config.startup_closed_loop_control"] == "1":
            self.request(8)

    def request(self, st):
        st = int(st)
        if st == 1:
            self.state, self.req = 1, None
            return
        if any(self.errs[k] for k in ("axis", "motor", "encoder", "controller")):
            return
        if st == 4:
            self.state, self.req, self.req_t = 4, 4, time.perf_counter()
        elif st == 6:
            if self.v.get("axis0.encoder.config.use_index") != "1":
                self.errs["axis"] |= 0x1
                return
            self.state, self.req, self.req_t = 6, 6, time.perf_counter()
        elif st == 7:
            if not self.motor_cal:
                self.errs["axis"] |= 0x1
                return
            self.state, self.req, self.req_t = 7, 7, time.perf_counter()
        elif st == 8:
            if not self.enc_ready:
                self.errs["motor"] |= 0x04000000
                self.errs["axis"] |= 0x40
                self.state = 1
                return
            self.state, self.req = 8, None
        elif st == 3:
            self.request(4)
        else:
            self.errs["axis"] |= 0x1

    # ------------------------------------------------------------ simulation
    def step(self):
        now = time.perf_counter()
        dt, self.last = min(0.02, now - self.last), now
        if self.booting and now >= self.online_at:
            self._boot_sequence()
        rng = self.f("axis.range", 900)
        kt = max(1e-3, self.f("axis0.motor.config.torque_constant", 0.5))
        ilim = self.f("axis0.motor.config.current_lim", 10)
        tmax = self.f("axis.maxtorque", 3)
        torque = 0.0
        if self.state == 4:
            if now - self.req_t > 3.0:
                self.v["axis0.motor.config.phase_resistance"] = "0.276700"
                self.v["axis0.motor.config.phase_inductance"] = "0.000616"
                self.motor_cal = True
                self.state, self.req = 1, None
                if self.chain and self.v["axis0.config.startup_encoder_offset_calibration"] == "1":
                    self.request(7)
                elif self.chain and self.v["axis0.config.startup_closed_loop_control"] == "1":
                    self.request(8)
        elif self.state == 6:
            # recherche d'index : le moteur avance au plus d'un tour jusqu'au repère Z
            self.pos += 0.4 * dt
            if now - self.req_t > 1.0:
                self.index_found = True
                if self.v.get("axis0.encoder.config.pre_calibrated") == "1":
                    self.enc_ready = True          # calage gardé, relatif à l'index
                self.state, self.req = 1, None
                if self.chain and self.enc_ready and self.v["axis0.config.startup_closed_loop_control"] == "1":
                    self.request(8)
                self.chain = False
        elif self.state == 7:
            ph = (now - self.req_t)
            self.pos = 0.5 * math.sin(min(ph, 4.0) / 4.0 * 2 * math.pi)   # ~1 tour aller-retour
            self.vel = 0.5 * 2 * math.pi / 4 * math.cos(min(ph, 4.0) / 4.0 * 2 * math.pi)
            if ph > 4.0:
                self.enc_ready = True
                self.v["axis0.encoder.config.direction"] = "1"
                self.state, self.req = 1, None
                if self.chain and self.v["axis0.config.startup_closed_loop_control"] == "1":
                    self.request(8)
                self.chain = False
        if self.state != 7:
            # mouvement « humain » + forces simulées
            t = now - self.t0
            hand = (0.55 * math.sin(t * 0.55) + 0.15 * math.sin(t * 2.1)) * (rng / 720.0)
            if self.state == 8:
                half = rng / 360.0 / 2
                x = self.pos / half if half else 0
                spring = -self.f("axis.idlespring") / 255.0 * tmax * x
                damp = -self.f("axis.axisdamper") / 255.0 * 0.4 * self.vel
                road = 0.25 * tmax * math.sin(t * 23) * (0.5 + 0.5 * math.sin(t * 0.7))
                stop = 0.0
                if abs(x) > 1:
                    stop = -math.copysign((abs(x) - 1) * self.f("axis.esgain") / 255.0 * 40 * tmax, x)
                torque = max(-tmax, min(tmax, spring + damp + road * self.f("axis.fxratio", 0.8) + stop))
                torque = max(-kt * ilim, min(kt * ilim, torque))
            acc = (hand - self.pos) * 18 - self.vel * 6 + torque * 4
            self.vel += acc * dt
            self.pos += self.vel * dt
        self.torque = torque
        self.iq = torque / kt + random.uniform(-0.04, 0.04) if self.state == 8 else random.uniform(-0.02, 0.02)
        vbus0 = 39.6
        r = max(0.05, self.f("axis0.motor.config.phase_resistance", 0.27) or 0.27)
        p_mech = torque * self.vel * 2 * math.pi
        p_cu = 1.5 * r * self.iq ** 2
        ibus = (p_cu + p_mech) / vbus0
        ibrake = 0.0
        if ibus < 0 and self.v.get("config.enable_brake_resistor") == "1":
            ibrake, ibus = -ibus * 0.95, ibus * 0.05
        self.temp += (31 + abs(self.iq) * 1.2 - self.temp) * dt * 0.05
        vbus = vbus0 - ibus * 0.06 + random.uniform(-0.03, 0.03)
        ov = self.f("config.dc_bus_overvoltage_trip_level", 46)
        if vbus > ov and self.state == 8:
            self.errs["system"] |= 0x4
            self.errs["motor"] |= 0x01000000
            self.state = 1
        return P.Telemetry(
            t=now, pos=0, pos_raw=int(max(-32767, min(32767, (self.pos * 360) / (rng / 2) * 32767))),
            vel=self.vel, iq=self.iq, torque=torque, vbus=vbus, ibus=ibus + random.uniform(-0.01, 0.01),
            ibrake=ibrake, fet_c=self.temp, motor_c=None, state=self.state, axis_err=self.errs["axis"],
            motor_err=self.errs["motor"], enc_err=self.errs["encoder"], ctrl_err=self.errs["controller"],
            buttons=0)


class FakeLink:
    name = T("DÉMO")

    def __init__(self, dev: FakeDevice):
        self.d = dev
        self.port = "DEMO"

    @staticmethod
    def find():
        return "DEMO"

    def close(self):
        pass

    def _chk(self):
        if not self.d.online():
            raise LinkLost(T("carte injoignable"))
        time.sleep(0.003)

    def offb(self, cmd, timeout=0.8):
        self._chk()
        m = re.match(r"^(\w+)\.(?:(\d+)\.)?(\w+)([?=!])?(.*)$", cmd)
        if not m:
            return None
        cls, inst, name, typ, val = m.groups()
        key = f"{cls}.{inst}.{name}" if inst else f"{cls}.{name}"
        d = self.d
        with d.lock:
            if key == "sys.save":
                d.ram.update({k: v for k, v in d.v.items() if P.is_offb(k)})
                return "OK"
            if key == "axis.zeroenc":
                d.v["axis.zeroofs"] = f"{d.pos * 360:.3f}"
                d.pos = 0.0
                return "OK"
            if key == "sys.errorsclr":
                return "OK"
            if key == "sys.fxtest":
                return f"ffb=0 pos={d.pos * 360:.1f} spd={d.vel * 360:.1f} trq={d.torque:.3f} fx=0"
            if key == "sys.temp":
                return f"{d.temp:.1f}"
            if key == "sys.uptime":
                return f"{int((time.perf_counter() - d.t0) * 1000)}ms"
            if key == "sys.savestat":
                return "writes=24 errors=0"
            if key == "sys.ping":
                return "pong"
            if key not in d.v:
                return "NOT_FOUND"
            if typ == "=":
                f = P.BY_PATH.get(key)
                try:
                    x = float(val)
                    if f:
                        lo, hi = (f.lo / f.scale, f.hi / f.scale) if f.kind not in ("bool", "enum") else (0, 9999)
                        x = max(min(lo, hi), min(max(lo, hi), x))
                    d.v[key] = str(int(x)) if (f and f.kind in ("int", "enum", "bool")) else f"{x:.2f}"
                except ValueError:
                    return "ERR"
            return d.v[key]

    def r(self, path, timeout=0.5):
        self._chk()
        d = self.d
        with d.lock:
            if path == "axis0.current_state":
                return str(d.state)
            if path == "axis0.encoder.is_ready":
                return "1" if d.enc_ready else "0"
            if path == "axis0.motor.is_calibrated":
                return "1" if d.motor_cal else "0"
            if path == "vbus_voltage":
                return "39.600000"
            if path == "error":
                return str(d.errs["system"])
            if path in ("axis0.encoder.shadow_count", "axis0.encoder.pos_estimate_counts"):
                cpr = int(d.f("axis0.encoder.config.cpr", 45000))
                return str(int(d.pos * cpr))
            if path == "axis0.encoder.count_in_cpr":
                cpr = int(d.f("axis0.encoder.config.cpr", 45000))
                return str(int(d.pos * cpr) % cpr)
            if path == "axis0.encoder.index_found":
                return "1" if d.index_found else "0"
            if path == "axis0.encoder.pos_estimate":
                return f"{d.pos:f}"
            if path == "axis0.encoder.vel_estimate":
                return f"{d.vel:f}"
            if path == "axis0.encoder.config.phase_offset":
                return "1234" if d.enc_ready else "0"
            if path in ("axis0.error", "axis0.motor.error", "axis0.encoder.error", "axis0.controller.error"):
                g = path.split(".")[1] if path.count(".") > 1 else "axis"
                return str(d.errs[{"axis0": "axis"}.get(g, g)])
            return d.v.get(path, "invalid property")

    def w(self, path, value, timeout=0.5):
        self._chk()
        d = self.d
        with d.lock:
            if path == "axis0.requested_state":
                d.request(int(float(value)))
                return True, value
            if path in ("axis0.error", "axis0.motor.error", "axis0.encoder.error", "axis0.controller.error"):
                g = {"axis0.error": "axis"}.get(path, path.split(".")[1])
                d.errs[g] = 0
                return True, "0"
            if path not in d.v:
                return False, "invalid property"
            f = P.BY_PATH.get(path)
            if f and f.ro:
                return False, "not implemented"
            if f and f.kind == "float":
                try:
                    d.v[path] = f"{float(value):f}"[:9]
                except ValueError:
                    return False, "not implemented"
            else:
                d.v[path] = str(int(float(value)))
            return True, d.v[path]

    def system(self, cmd):
        self._chk()
        d = self.d
        with d.lock:
            if cmd == "sc":
                d.errs = {k: 0 for k in d.errs}
            elif cmd == "ss":
                if d.state != 1:
                    return
                d.ram.update({k: v for k, v in d.v.items() if not P.is_offb(k)})
                d.reboot()
            elif cmd == "sr":
                d.reboot()
            elif cmd == "se":
                d.ram = {k: v for k, v in d.ram.items() if P.is_offb(k) or k.startswith(("hw_", "fw_", "serial"))}
                FakeDevice.__init__(d)
                d.reboot()
            elif cmd == "sd":
                d.dfu = True

    def raw(self, line, idle=0.25, total=2.0):
        line = line.strip()
        if not line:
            return []
        if line.startswith("r "):
            return [self.r(line[2:].strip())]
        if line.startswith("w "):
            parts = line.split(None, 2)
            if len(parts) < 3:
                return ["invalid command format"]
            ok, msg = self.w(parts[1], parts[2])
            return [] if ok else [msg]
        if line in ("ss", "sr", "sc", "sd", "se"):
            self.system(line)
            return []
        if "." in line and re.search(r"[?=!]", line):
            v = self.offb(line)
            return [f"[{line}|{v}]"]
        if line == "I":
            return ["Ibus=-0.12..3.40 Mot=-0.10..3.38 V=39.20..40.10"]
        return ["unknown command"]


# ======================================================================
#  Threads
# ======================================================================
class SerialThread(QThread):
    def __init__(self, board: "Board"):
        super().__init__()
        self.b = board
        self.q: queue.Queue = queue.Queue()
        self.urgent: collections.deque = collections.deque()
        self.link = None
        self._run = True
        self.suspend_until = 0.0

    def put(self, *job):
        self.q.put(job)

    def put_urgent(self, *job):
        self.urgent.append(job)

    def run(self):
        next_try = 0.0
        while self._run:
            if self.link is None:
                now = time.perf_counter()
                if now < max(next_try, self.suspend_until):
                    time.sleep(0.05)
                    # les travaux urgents (STOP) attendent la reconnexion, les autres sont refusés
                    self._reject_pending()
                    continue
                next_try = now + 1.0
                self._open()
                continue
            try:
                if self.urgent:
                    job = self.urgent.popleft()
                else:
                    try:
                        job = self.q.get(timeout=0.03)
                    except queue.Empty:
                        continue
                self._do(job)
            except LinkLost as e:
                self._lost(str(e))
            except Exception as e:  # ne jamais laisser mourir le thread
                self.b.log.emit("error", f"{type(e).__name__}: {e}")
                self.b.log.emit("debug", traceback.format_exc())
        if self.link:
            self.link.close()

    def _reject_pending(self):
        while True:
            try:
                job = self.q.get_nowait()
            except queue.Empty:
                return
            if job[0] == "write":
                self.b.write_done.emit(job[1], False, None, T("carte non connectée"))
            elif job[0] == "raw":
                self.b.console.emit("err", T("Port série non connecté."))
            elif job[0] in ("save", "state", "clear", "recenter", "system"):
                self.b.log.emit("warn", T("Commande ignorée : carte non connectée."))

    def _open(self):
        try:
            port = self.b.link_cls.find()
            if not port:
                return
            self.link = self.b.make_link(port)
            ident = self.link.offb("sys.hwtype?")
            if ident is None:
                # pas notre firmware (ou carte qui démarre encore) : on réessaiera
                self.link.close()
                self.link = None
                self.b.log.emit("debug", f"{port}: sys.hwtype sans réponse")
                return
        except LinkLost as e:
            self.link = None
            self.b.log.emit("debug", f"open: {e}")
            return
        self.b.serial_ok = True
        self.b.link_changed.emit({"serial": True, "port": self.link.port, "hwtype": ident,
                                  "backend": self.link.name})
        self.b.log.emit("info", T("Port série {p} ouvert ({h})").format(p=self.link.port, h=ident))
        if self.b.estop:
            self.urgent.appendleft(("estop_on",))
        self._read_all()

    def _lost(self, why):
        if self.link:
            self.link.close()
        self.link = None
        if self.b.serial_ok:
            self.b.serial_ok = False
            self.b.link_changed.emit({"serial": False, "why": why})
            self.b.log.emit("warn", T("Port série perdu ({w})").format(w=why))

    # ------------------------------------------------------------ travaux
    def _get(self, path):
        if P.is_offb(path):
            v = self.link.offb(path + "?")
            return None if v in (None, "NOT_FOUND", "ERR") else v
        v = self.link.r(path)
        return None if (v is None or v in P.ASCII_ERRORS) else v

    def _service_urgent(self):
        """Exécute tout de suite un STOP arrivé pendant un long travail (lecture complète…)."""
        while self.urgent:
            self._do(self.urgent.popleft())

    def _read_all(self):
        paths = [f.path for f in P.FIELDS] + [g.path for g in P.GPIO_GLOBAL] + P.EQ_INFO + P.IDENTITY
        paths += [f"gpio.{p}.{n}" for p in P.GPIO_PINS for n in P.GPIO_FIELDS]
        out = {}
        for i, p in enumerate(paths):
            if not self._run:
                return                          # fermeture de l'appli : inutile de finir
            self._service_urgent()
            out[p] = self._get(p)
            if i % 12 == 11:
                self.b.progress.emit(i + 1, len(paths))
        self.b.progress.emit(len(paths), len(paths))
        rng = P.BY_PATH["axis.range"].parse(out.get("axis.range"))
        if rng:
            self.b.half_range = rng / 2
        missing = [p for p in paths if out[p] is None]
        self.b.values.emit(out, "all")
        self.b.log.emit("info", T("Réglages lus ({n} valeurs)").format(n=len(paths) - len(missing)))
        if missing:
            self.b.log.emit("warn", T("Non disponibles sur ce firmware : {l}").format(l=", ".join(missing)))

    def _do(self, job):
        kind = job[0]
        L = self.link
        b = self.b
        if kind in ("read", "probe"):
            _, paths, tag = job
            out = {}
            for p in paths:
                self._service_urgent()
                out[p] = self._get(p)
            b.values.emit(out, tag)
        elif kind == "read_all":
            self._read_all()
        elif kind == "write":
            _, path, text = job
            f = P.BY_PATH.get(path)
            if P.is_offb(path):
                v = L.offb(f"{path}={text}")
                ok = v not in (None, "NOT_FOUND", "ERR")
                msg = v if ok else (v or T("pas de réponse"))
            else:
                ok, msg = L.w(path, text)
            if ok:
                if path == "axis.range":
                    rv = P.BY_PATH["axis.range"].parse(msg)
                    if rv:
                        b.half_range = rv / 2
                b.log.emit("info", f"→ {path} = {text}" + ("" if (f is None or f.same(f.parse(text), f.parse(msg)))
                                                         else "  " + T("(la carte a retenu {v})").format(v=msg)))
            else:
                b.log.emit("warn", T("Écriture refusée : {p} = {v} ({m})").format(p=path, v=text, m=msg))
            b.write_done.emit(path, ok, msg if ok else None, "" if ok else msg)
        elif kind == "raw":
            _, line = job
            lines = L.raw(line)
            b.console.emit("rx", "\n".join(lines) if lines else T("(pas de réponse)"))
            if line.strip() in ("ss", "sr", "sd", "se"):
                self._expect_reboot(line.strip())
        elif kind == "state":
            _, st = job
            if int(st) == P.CLOSED_LOOP:
                self._closed_loop()
                return
            tm = b.last
            if int(st) != P.IDLE and tm is not None and tm.any_error:
                # l'ODrive refuse tout changement d'état tant qu'une erreur est présente : on la note puis on efface
                b.log.emit("warn", T("Erreurs effacées avant la commande : {e}").format(
                    e=", ".join(n for _g, n, _d in P.errors_of(tm))))
                L.system("sc")
                time.sleep(0.15)
            ok, msg = L.w("axis0.requested_state", str(int(st)))
            b.log.emit("info" if ok else "warn",
                       T("→ état demandé : {s}").format(s=P.state_text(int(st))) + ("" if ok else f" ({msg})"))
        elif kind == "clear":
            L.system("sc")
            b.log.emit("info", T("→ erreurs effacées (résistance de freinage réarmée)"))
            time.sleep(0.1)
            b.values.emit({"error": self._get("error")}, "error")
        elif kind == "recenter":
            v = L.offb("axis.zeroenc!")
            b.log.emit("info", T("→ centre du volant pris à la position actuelle ({v})").format(v=v))
            b.values.emit({"axis.zeroofs": self._get("axis.zeroofs")}, "zero")
        elif kind == "estop_on":
            ok, msg = L.w("axis0.requested_state", "1")
            b.log.emit("warn" if ok else "error",
                       T("STOP : axe mis au repos, moteur non alimenté") if ok
                       else T("STOP : commande refusée ({m})").format(m=msg))
        elif kind == "estop_off":
            arm = job[1] if len(job) > 1 else True
            if not arm:
                b.log.emit("info", T("STOP réarmé, moteur laissé au repos"))
                return
            b.log.emit("info", T("STOP réarmé"))
            self._closed_loop()
        elif kind == "save":
            _, ffb, odrive = job
            if ffb:
                v = L.offb("sys.save!", timeout=3.0)
                if v == "OK":
                    b.log.emit("info", T("Réglages volant et effets mémorisés (sys.save)"))
                    b.saved.emit("ffb", True, "")
                else:
                    b.log.emit("error", T("Mémorisation volant/effets refusée ({v})").format(v=v))
                    b.saved.emit("ffb", False, str(v))
                    return
            if odrive:
                L.w("axis0.requested_state", "1")
                t_end = time.perf_counter() + 2.0
                while time.perf_counter() < t_end:
                    if L.r("axis0.current_state") == "1":
                        break
                    time.sleep(0.1)
                else:
                    b.log.emit("error", T("Le moteur ne s'est pas mis au repos : réglages ODrive non mémorisés."))
                    b.saved.emit("odrive", False, T("moteur pas au repos"))
                    return
                L.system("ss")
                b.saved.emit("odrive", True, "")
                self._expect_reboot("ss")
        elif kind == "system":
            _, cmd = job
            L.system(cmd)
            if cmd in ("sr", "sd", "se", "ss"):
                self._expect_reboot(cmd)

    def _closed_loop(self):
        """Active le moteur (bouton et réarmement du STOP) : volant dans sa course, codeur calé, erreurs effacées,
        puis vérifie que la carte est vraiment passée en boucle fermée."""
        b, L = self.b, self.link
        tm = b.last
        if tm is not None and abs(tm.pos_raw) >= 32700:
            # hors course, la butée renverrait le volant d'un coup dès l'activation (à-coup puis erreur)
            msg = T("Le volant est hors de sa course réglée (±{r:.0f}°) : ramène-le dans la course, puis active le "
                    "moteur. Sinon la butée le renvoie d'un coup.").format(r=b.half_range)
            b.log.emit("warn", msg)
            b.arm_refused.emit(msg)
            return
        if L.r("axis0.encoder.is_ready") != "1":
            b.log.emit("warn", T("Boucle fermée refusée : le codeur n'est pas calé depuis l'allumage."))
            b.rearm_needs_cal.emit()
            return
        # toujours : une erreur absente de la télémétrie (rapport HID pas encore reçu…) bloque aussi l'activation
        if tm is not None and tm.any_error:
            b.log.emit("warn", T("Erreurs effacées avant la commande : {e}").format(
                e=", ".join(n for _g, n, _d in P.errors_of(tm))))
        L.system("sc")
        time.sleep(0.15)
        ok, msg = L.w("axis0.requested_state", str(P.CLOSED_LOOP))
        b.log.emit("info" if ok else "warn",
                   T("→ état demandé : {s}").format(s=P.state_text(P.CLOSED_LOOP)) + ("" if ok else f" ({msg})"))
        t_end = time.perf_counter() + 1.5
        while time.perf_counter() < t_end:
            st = L.r("axis0.current_state")
            if st == str(P.CLOSED_LOOP):
                return
            time.sleep(0.1)
        err = L.r("axis0.error")
        msg = T("La carte n'a pas activé le moteur (état {s}, erreur d'axe {e}). Regarde le Moniteur, efface les "
                "erreurs puis réessaie.").format(s=st, e=err)
        b.log.emit("error", msg)
        b.arm_refused.emit(msg)

    def _expect_reboot(self, cmd):
        what = {"ss": T("mémorisation + redémarrage"), "sr": T("redémarrage"), "sd": T("mode DFU"),
                "se": T("effacement de la configuration")}[cmd]
        b = self.b
        b.log.emit("warn", T("La carte redémarre ({w})…").format(w=what))
        if self.link:
            self.link.close()
        self.link = None
        b.serial_ok = False
        b.link_changed.emit({"serial": False, "why": what, "rebooting": cmd != "sd"})
        self.suspend_until = time.perf_counter() + (1.2 if cmd != "sd" else 5.0)


class HidThread(QThread):
    def __init__(self, board: "Board"):
        super().__init__()
        self.b = board
        self._run = True
        self.dev = None
        self._t_inside = time.perf_counter()
        self._t_over = None
        self._t_err = None
        self._stats = {}
        self._t_idle_cmd = 0.0
        self._t_last = time.perf_counter()

    def run(self):
        next_try = 0.0
        while self._run:
            now = time.perf_counter()
            if self.dev is None:
                if now < next_try:
                    time.sleep(0.05)
                    continue
                next_try = now + 1.0
                self._open()
                continue
            try:
                tm = self._read()
            except Exception as e:
                self._lost(f"{type(e).__name__}: {e}")
                continue
            if tm is None:
                continue
            try:
                self._watch(tm)
            except Exception as e:  # ne jamais laisser mourir le thread : il porte la surveillance de survitesse
                self.b.log.emit("error", f"{type(e).__name__}: {e}")
                self.b.log.emit("debug", traceback.format_exc())
            self.b.last = tm
            with self.b.tm_lock:
                self.b.tm_buf.append(tm)          # vidé par l'IHM à 30 Hz (pas de file de signaux qui s'accumule)
        self._close()

    # -------------------------------------------------------- source
    def _open(self):
        if self.b.demo:
            if not self.b.fake.online():
                return
            self.dev = "demo"
        else:
            if hid is None:
                return
            ents = list(hid.enumerate(P.VID, P.PID))
            if not ents:
                return
            # collection « joystick » (page 1, usage 4) de préférence : c'est elle qui porte le rapport n°1
            ent = next((e for e in ents if e.get("usage_page") == 0x01 and e.get("usage") in (4, 5)),
                       next((e for e in ents if e.get("usage_page") == 0x01), ents[0]))
            try:
                d = hid.device()
                d.open_path(ent["path"])
                d.set_nonblocking(False)
                self.dev = d
                self._t_last = time.perf_counter()
                self._t_err = None
                self._stats = {}
                self.b.log.emit("info", T("HID ouvert : {p} (usage {u:04X}:{v:04X}, {n} interface(s) trouvée(s))").format(
                    p=ent.get("product_string") or "?", u=ent.get("usage_page", 0), v=ent.get("usage", 0), n=len(ents)))
            except Exception as e:
                self.b.log.emit("debug", f"hid open: {e}")
                return
        self.b.hid_ok = True
        self.b.link_changed.emit({"hid": True})
        self.b.log.emit("info", T("Télémétrie HID reçue (1 kHz)"))

    def _close(self):
        if self.dev not in (None, "demo"):
            try:
                self.dev.close()
            except Exception:
                pass
        self.dev = None

    def _lost(self, why):
        self._close()
        if self.b.hid_ok:
            self.b.hid_ok = False
            self.b.link_changed.emit({"hid": False, "why": why})
            st = self._stats
            self.b.log.emit("warn", T("Télémétrie HID perdue ({w}). Depuis l'ouverture : {n} rapports n°1, "
                                      "{o} autres rapports, {e} erreurs de lecture.").format(
                w=why, n=st.get("ok", 0), o=st.get("other", 0), e=st.get("err", 0)))

    def _read(self):
        hr = self.b.half_range or 450.0
        if self.dev == "demo":
            fk = self.b.fake
            if not fk.online():
                raise OSError(T("carte injoignable"))
            time.sleep(0.002)
            with fk.lock:
                tm = fk.step()
            return P.parse_report(P.build_report(tm), tm.t, hr)
        try:
            r = self.dev.read(256, 50)            # tampon large : Windows refuse un tampon plus court que le rapport
        except (OSError, ValueError):
            # erreur ponctuelle (Windows) : on ne lâche la liaison que si elle dure
            now = time.perf_counter()
            self._stats["err"] = self._stats.get("err", 0) + 1
            if self._t_err is None:
                self._t_err = now
            if now - self._t_err > 1.0:
                raise
            time.sleep(0.005)
            return None
        self._t_err = None
        now = time.perf_counter()
        if not r:
            if now - self._t_last > 3.0:          # carte en DFU, firmware arrêté…
                raise OSError(T("plus de rapport HID"))
            return None
        tm = P.parse_report(bytes(r), now, hr)
        if tm is not None:
            self._t_last = now
            self._stats["ok"] = self._stats.get("ok", 0) + 1
        else:
            self._stats["other"] = self._stats.get("other", 0) + 1
            self._stats["last_other"] = bytes(r[:4]).hex(" ")
        return tm

    # -------------------------------------------------------- sécurité
    def _watch(self, tm: P.Telemetry):
        b = self.b
        now = tm.t
        # maintien du STOP : si quelque chose réarme le moteur, on le remet au repos
        if b.estop and tm.state == P.CLOSED_LOOP and now - self._t_idle_cmd > 0.5:
            self._t_idle_cmd = now
            b.ser.put_urgent("estop_on")
        if abs(tm.pos_raw) < 32700:
            self._t_inside = now
        if not b.guard_armed or b.estop:
            return
        spd = tm.speed_dps
        out = b.guard_range and now - self._t_inside > 0.15
        # survitesse : instantanée pendant les essais de force ; pendant une calibration, il faut qu'elle dure
        # (au début du calage, le rotor « saute » sur l'angle imposé : pointe de vitesse de quelques ms, normale)
        if abs(spd) > b.guard_limit:
            if self._t_over is None:
                self._t_over = now
            over = now - self._t_over >= b.guard_sustain
        else:
            self._t_over = None
            over = False
        if over or out:
            b.set_estop(True)
            b.guard_tripped.emit(spd if not out else float("inf"))
            b.log.emit("error", (T("SURVITESSE {v} °/s").format(v=f"{spd:.0f}") if not out
                                 else T("DÉPASSEMENT DE COURSE")) + " → " + T("STOP"))


class Board(QObject):
    link_changed = Signal(dict)
    values = Signal(dict, str)             # {chemin: texte ou None}, étiquette
    write_done = Signal(str, bool, object, str)
    telemetry = Signal(list)               # [Telemetry]
    log = Signal(str, str)
    console = Signal(str, str)             # ("rx"|"err", texte)
    progress = Signal(int, int)
    saved = Signal(str, bool, str)
    estop_changed = Signal(bool)
    guard_tripped = Signal(float)
    rearm_needs_cal = Signal()
    arm_refused = Signal(str)              # activation du moteur refusée ou ratée : message pour l'utilisateur

    def __init__(self, demo=False, parent=None):
        super().__init__(parent)
        self.demo = demo
        self.fake = FakeDevice() if demo else None
        self.link_cls = FakeLink if demo else SerialLink
        self.serial_ok = False
        self.hid_ok = False
        self.half_range = 450.0
        self.last: P.Telemetry | None = None
        self.estop = False
        self.guard_armed = False
        self.guard_range = True
        self.guard_sustain = 0.0
        self.guard_limit = 720.0
        self.tm_lock = threading.Lock()
        self.tm_buf: collections.deque = collections.deque(maxlen=5000)   # 5 s maxi si l'IHM est bloquée
        self._pump = QTimer(self)
        self._pump.setInterval(33)
        self._pump.timeout.connect(self._pump_tm)
        self.ser = SerialThread(self)
        self.hidt = HidThread(self)

    def make_link(self, port):
        return FakeLink(self.fake) if self.demo else SerialLink(port)

    def start(self):
        self.ser.start()
        self.hidt.start()
        self._pump.start()

    def _pump_tm(self):
        """Thread IHM : distribue d'un coup tout ce que le thread HID a reçu depuis le dernier tour."""
        with self.tm_lock:
            if not self.tm_buf:
                return
            batch = list(self.tm_buf)
            self.tm_buf.clear()
        self.telemetry.emit(batch)

    def stop(self):
        self.ser._run = False
        self.hidt._run = False
        self.ser.wait(1500)
        self.hidt.wait(1500)

    # ------------------------------------------------------------ API
    @property
    def connected(self):
        return self.serial_ok

    @property
    def state(self):
        return self.last.state if (self.last and self.hid_ok) else None

    def read(self, paths, tag=""):
        self.ser.put("read", list(paths), tag)

    def read_all(self):
        self.ser.put("read_all")

    def write(self, path: str, raw_value):
        f = P.BY_PATH.get(path)
        text = f.fmt(raw_value) if f else str(raw_value)
        self.ser.put("write", path, text)

    def raw(self, line: str):
        self.ser.put("raw", line)

    def request_state(self, st: int):
        if self.estop and st not in (1,):
            self.log.emit("warn", T("STOP enclenché : réarme-le avant d'activer le moteur."))
            return False
        self.ser.put("state", int(st))
        return True

    def clear_errors(self):
        self.ser.put("clear")

    def recenter(self):
        self.ser.put("recenter")

    def save(self, ffb=True, odrive=False):
        self.ser.put("save", ffb, odrive)

    def system(self, cmd):
        self.ser.put("system", cmd)

    def set_estop(self, on: bool, arm: bool = False):
        """STOP : axe au repos (moteur non alimenté). Au réarmement, arm=True redemande la boucle fermée."""
        if on == self.estop:
            return
        self.estop = on
        if on:
            self.hidt._t_idle_cmd = time.perf_counter()   # évite un 2e « repos » immédiat par la surveillance HID
            self.ser.put_urgent("estop_on")
            if not self.serial_ok:
                self.log.emit("error", T("STOP : port série non connecté, la carte n'a pas pu être mise au repos ! "
                                         "Coupe l'alimentation."))
        else:
            self.ser.put("estop_off", arm)
        self.estop_changed.emit(on)

    def arm_guard(self, armed: bool, limit_dps: float | None = None, range_check: bool = True,
                  sustain_s: float = 0.0):
        """Surveillance pendant un essai : survitesse, et sortie de la course réglée si range_check
        (pas pendant le calage du codeur, qui fait faire un tour au moteur où qu'il soit)."""
        if armed and not self.guard_armed:
            self.hidt._t_inside = time.perf_counter()    # un volant déjà en butée ne déclenche pas tout de suite
        self.hidt._t_over = None
        self.guard_armed = armed
        self.guard_range = range_check
        self.guard_sustain = float(sustain_s)
        if limit_dps:
            self.guard_limit = float(limit_dps)
