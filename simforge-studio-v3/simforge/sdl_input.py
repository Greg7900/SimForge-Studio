"""
Lecture joystick + effets de retour de force DirectInput via SDL2 (pysdl2).
C'est le même chemin que celui des jeux : on teste donc le volant « comme un jeu ».
Toutes les fonctions sont appelées depuis le thread de l'IHM (QTimer).
"""
from __future__ import annotations

from .i18n import T

import ctypes

SDL_OK = False
SDL_ERR = ""
try:
    import sdl2  # type: ignore  (SDL2.dll fourni par le paquet pysdl2-dll)
    SDL_OK = True
except Exception as e:  # pragma: no cover
    sdl2 = None
    SDL_ERR = str(e)


def _err() -> str:
    try:
        return sdl2.SDL_GetError().decode(errors="ignore")
    except Exception:
        return "?"


class SdlInput:
    def __init__(self):
        self.ok = False
        self.error = SDL_ERR
        self.js = None
        self.js_index = -1
        self.haptic = None
        self.effects: dict[str, int] = {}
        self.caps = 0
        if not SDL_OK:
            return
        for k, v in ((b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1"),
                     # forcer DirectInput : indispensable pour le retour de force
                     (b"SDL_JOYSTICK_RAWINPUT", b"0"),
                     (b"SDL_JOYSTICK_HIDAPI", b"0"),
                     (b"SDL_JOYSTICK_WGI", b"0")):
            sdl2.SDL_SetHint(k, v)
        if sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_HAPTIC | sdl2.SDL_INIT_EVENTS) != 0:
            self.error = _err()
            return
        self.ok = True

    # ------------------------------------------------------------ joystick
    def devices(self) -> list[str]:
        if not self.ok:
            return []
        out = []
        for i in range(sdl2.SDL_NumJoysticks()):
            n = sdl2.SDL_JoystickNameForIndex(i)
            out.append(n.decode(errors="ignore") if n else f"Joystick {i}")
        return out

    def poll_hotplug(self) -> bool:
        """Retourne True si la liste des périphériques a changé."""
        if not self.ok:
            return False
        changed = False
        ev = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(ev)):
            if ev.type in (sdl2.SDL_JOYDEVICEADDED, sdl2.SDL_JOYDEVICEREMOVED):
                changed = True
        return changed

    def open(self, index: int) -> bool:
        self.close()
        if not self.ok or index < 0:
            return False
        js = sdl2.SDL_JoystickOpen(index)
        if not js:
            self.error = _err()
            return False
        self.js, self.js_index = js, index
        return True

    def close(self):
        self.close_haptic()
        if self.js:
            sdl2.SDL_JoystickClose(self.js)
        self.js, self.js_index = None, -1

    def read(self):
        """-> (axes[int16], buttons[bool], hats[int]) ou None."""
        if not self.js:
            return None
        sdl2.SDL_JoystickUpdate()
        if not sdl2.SDL_JoystickGetAttached(self.js):
            return None
        na = sdl2.SDL_JoystickNumAxes(self.js)
        nb = sdl2.SDL_JoystickNumButtons(self.js)
        nh = sdl2.SDL_JoystickNumHats(self.js)
        axes = [sdl2.SDL_JoystickGetAxis(self.js, i) for i in range(max(0, na))]
        btns = [bool(sdl2.SDL_JoystickGetButton(self.js, i)) for i in range(max(0, nb))]
        hats = [sdl2.SDL_JoystickGetHat(self.js, i) for i in range(max(0, nh))]
        return axes, btns, hats

    # ------------------------------------------------------------ haptique
    def haptic_devices(self) -> list[str]:
        if not self.ok:
            return []
        return [(sdl2.SDL_HapticName(i) or b"?").decode(errors="ignore")
                for i in range(sdl2.SDL_NumHaptics())]

    def open_haptic(self, prefer_name: str = "") -> str:
        """Ouvre le retour de force. Retourne '' si OK, sinon le message d'erreur."""
        self.close_haptic()
        if not self.ok:
            return self.error or T("SDL2 indisponible")
        h = None
        if self.js and sdl2.SDL_JoystickIsHaptic(self.js) == 1:
            h = sdl2.SDL_HapticOpenFromJoystick(self.js)
        if not h:
            names = self.haptic_devices()
            idx = next((i for i, n in enumerate(names) if prefer_name and prefer_name.lower() in n.lower()),
                       0 if names else -1)
            if idx >= 0:
                h = sdl2.SDL_HapticOpen(idx)
        if not h:
            e = _err()
            return T("Aucun périphérique à retour de force DirectInput trouvé (") + e + ")" if e else \
                T("Aucun périphérique à retour de force DirectInput trouvé (").rstrip(" (")
        self.haptic = h
        self.caps = sdl2.SDL_HapticQuery(h)
        if self.caps & sdl2.SDL_HAPTIC_AUTOCENTER:
            sdl2.SDL_HapticSetAutocenter(h, 0)
        if self.caps & sdl2.SDL_HAPTIC_GAIN:
            sdl2.SDL_HapticSetGain(h, 100)
        return ""

    def close_haptic(self):
        if self.haptic:
            try:
                sdl2.SDL_HapticStopAll(self.haptic)
                for eid in self.effects.values():
                    sdl2.SDL_HapticDestroyEffect(self.haptic, eid)
            except Exception:
                pass
            sdl2.SDL_HapticClose(self.haptic)
        self.haptic = None
        self.effects.clear()
        self.caps = 0

    def supported(self) -> dict[str, bool]:
        c = self.caps
        if not SDL_OK:
            return {}
        return {"constant": bool(c & sdl2.SDL_HAPTIC_CONSTANT),
                "spring": bool(c & sdl2.SDL_HAPTIC_SPRING),
                "damper": bool(c & sdl2.SDL_HAPTIC_DAMPER),
                "friction": bool(c & sdl2.SDL_HAPTIC_FRICTION),
                "inertia": bool(c & sdl2.SDL_HAPTIC_INERTIA),
                "sine": bool(c & sdl2.SDL_HAPTIC_SINE),
                "triangle": bool(c & sdl2.SDL_HAPTIC_TRIANGLE),
                "sawup": bool(c & sdl2.SDL_HAPTIC_SAWTOOTHUP),
                "sawdown": bool(c & sdl2.SDL_HAPTIC_SAWTOOTHDOWN),
                "ramp": bool(c & sdl2.SDL_HAPTIC_RAMP),
                "gain": bool(c & sdl2.SDL_HAPTIC_GAIN)}

    def set_gain(self, pct: int):
        if self.haptic and self.caps & sdl2.SDL_HAPTIC_GAIN:
            sdl2.SDL_HapticSetGain(self.haptic, max(0, min(100, int(pct))))

    @staticmethod
    def _dir(e):
        e.direction.type = sdl2.SDL_HAPTIC_CARTESIAN
        e.direction.dir[0] = 1
        e.direction.dir[1] = 0
        e.direction.dir[2] = 0

    def _build(self, kind: str, p: dict):
        e = sdl2.SDL_HapticEffect()
        s16 = lambda v: int(max(-32767, min(32767, v)))
        u16 = lambda v: int(max(0, min(65535, v)))
        inf = sdl2.SDL_HAPTIC_INFINITY
        if kind == "constant":
            e.type = sdl2.SDL_HAPTIC_CONSTANT
            c = e.constant
            c.type = sdl2.SDL_HAPTIC_CONSTANT
            self._dir(c)
            c.length = inf
            c.level = s16(p["level"] * 327.67)
        elif kind in ("spring", "damper", "friction", "inertia"):
            t = {"spring": sdl2.SDL_HAPTIC_SPRING, "damper": sdl2.SDL_HAPTIC_DAMPER,
                 "friction": sdl2.SDL_HAPTIC_FRICTION, "inertia": sdl2.SDL_HAPTIC_INERTIA}[kind]
            e.type = t
            c = e.condition
            c.type = t
            self._dir(c)
            c.length = inf
            for i in range(3):
                c.right_sat[i] = c.left_sat[i] = u16(p.get("saturation", 100) * 655.35)
                c.right_coeff[i] = c.left_coeff[i] = s16(p["coeff"] * 327.67)
                c.deadband[i] = u16(p.get("deadband", 0) * 655.35)
                c.center[i] = s16(p.get("center", 0) * 327.67)
        elif kind in ("sine", "triangle", "sawup", "sawdown"):
            t = {"sine": sdl2.SDL_HAPTIC_SINE, "triangle": sdl2.SDL_HAPTIC_TRIANGLE,
                 "sawup": sdl2.SDL_HAPTIC_SAWTOOTHUP, "sawdown": sdl2.SDL_HAPTIC_SAWTOOTHDOWN}[kind]
            e.type = t
            c = e.periodic
            c.type = t
            self._dir(c)
            c.length = inf
            c.period = max(1, int(p["period_ms"]))
            c.magnitude = s16(p["magnitude"] * 327.67)
            c.offset = s16(p.get("offset", 0) * 327.67)
            c.phase = 0
        elif kind == "ramp":
            e.type = sdl2.SDL_HAPTIC_RAMP
            c = e.ramp
            c.type = sdl2.SDL_HAPTIC_RAMP
            self._dir(c)
            c.length = max(1, int(p.get("length_ms", 2000)))
            c.start = s16(p["start"] * 327.67)
            c.end = s16(p["end"] * 327.67)
        else:
            raise ValueError(kind)
        return e

    def play(self, kind: str, params: dict) -> str:
        """Crée ou met à jour l'effet et le lance. '' si OK."""
        if not self.haptic:
            return T("Retour de force non ouvert")
        e = self._build(kind, params)
        if kind in self.effects:
            if sdl2.SDL_HapticUpdateEffect(self.haptic, self.effects[kind], ctypes.byref(e)) < 0:
                return _err()
            return ""
        eid = sdl2.SDL_HapticNewEffect(self.haptic, ctypes.byref(e))
        if eid < 0:
            return _err()
        self.effects[kind] = eid
        if sdl2.SDL_HapticRunEffect(self.haptic, eid, 1) < 0:
            return _err()
        return ""

    def stop(self, kind: str):
        if self.haptic and kind in self.effects:
            sdl2.SDL_HapticStopEffect(self.haptic, self.effects[kind])
            sdl2.SDL_HapticDestroyEffect(self.haptic, self.effects.pop(kind))

    def stop_all(self):
        if self.haptic:
            sdl2.SDL_HapticStopAll(self.haptic)
            for eid in self.effects.values():
                sdl2.SDL_HapticDestroyEffect(self.haptic, eid)
            self.effects.clear()

    def shutdown(self):
        self.close()
        if self.ok:
            sdl2.SDL_Quit()
