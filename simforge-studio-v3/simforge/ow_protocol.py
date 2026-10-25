"""
Protocole du firmware Odrive-Wheel (ODrive 0.5.6 + effets OpenFFBoard), écrit à partir de son code source.

Deux canaux USB :
  • HID (manette) : rapport d'entrée n°1 envoyé à 1 kHz, avec la télémétrie (position, vitesse, Iq, couple,
    tension et courant du bus, courant de la résistance de freinage, températures, état et erreurs).
  • Port série virtuel (CDC), deux syntaxes sur la même ligne :
      - OpenFFBoard :  "axis.range?"  →  "[axis.range?|900]"     (= écrit, ! exécute)
      - ODrive ASCII : "r axis0.motor.config.current_lim" → "10.000000"
                       "w <chemin> <valeur>"  (muet si OK)   ss = mémoriser + redémarrer, sr, sc, sd, se
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field

from .i18n import T

VID = 0x1209
PID = 0x0D40
REPORT_ID = 0x01

# classes de commandes OpenFFBoard (les autres chemins sont des propriétés ODrive)
OFFB_CLASSES = {"axis", "fx", "sys", "gpio", "main", "odrv", "effects"}


def to_float(s):
    """Texte de la carte → nombre, ou None s'il est absent ou illisible."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def is_offb(path: str) -> bool:
    return path.split(".", 1)[0] in OFFB_CLASSES


# ======================================================================
#  Télémétrie HID (ffb_defs.h : reportHID_t, ffb_task.cpp)
# ======================================================================
#  id u8 | buttons u64 | X Y Z RX RY RZ Dial Slider i16 | VBus IBus IBrake i16 | FetT MotT i8 |
#  AxisState i8 | AxisErr MotorErr EncErr CtrlErr i32
_HID = struct.Struct("<BQ8h3hbbbiiii")
HID_LEN = _HID.size          # 50 octets, id compris


@dataclass
class Telemetry:
    t: float                 # horloge PC (s)
    pos: float               # position volant, °  (X × course/2 / 32767)
    pos_raw: int             # X brut ±32767
    vel: float               # vitesse moteur, tr/s (vel_estimate)
    iq: float                # courant de couple mesuré, A
    torque: float            # couple commandé en sortie du contrôleur, N·m
    vbus: float              # V
    ibus: float              # A  (+ = consommé, − = renvoyé à l'alim)
    ibrake: float            # A  dans la résistance de freinage
    fet_c: float | None      # °C, None = pas de capteur
    motor_c: float | None
    state: int
    axis_err: int
    motor_err: int
    enc_err: int
    ctrl_err: int
    buttons: int
    axes: tuple = ()         # RX RY RZ Slider (entrées GPIO en mode axe)

    @property
    def any_error(self) -> bool:
        return bool(self.axis_err or self.motor_err or self.enc_err or self.ctrl_err)

    @property
    def speed_dps(self) -> float:
        return self.vel * 360.0


def parse_report(data: bytes, t: float, half_range: float) -> Telemetry | None:
    """Rapport d'entrée HID tel que rendu par hidapi (octet d'id en tête)."""
    if len(data) < 31 or data[0] != REPORT_ID:
        return None
    b = bytes(data[:HID_LEN])
    if len(b) < HID_LEN:     # firmware plus ancien sans températures/erreurs : on complète
        b = b + bytes(HID_LEN - len(b))
        short = True
    else:
        short = False
    (_id, buttons, x, y, z, rx, ry, rz, dial, slider, vb, ib, ibr,
     fet, mot, st, ae, me, ee, ce) = _HID.unpack(b)
    u32 = lambda v: v & 0xFFFFFFFF
    return Telemetry(
        t=t, pos=x / 32767.0 * half_range, pos_raw=x, vel=y / 1000.0, iq=z / 1000.0, torque=dial / 1000.0,
        vbus=vb / 100.0, ibus=ib / 100.0, ibrake=ibr / 100.0,
        fet_c=None if (short or fet == -128) else float(fet),
        motor_c=None if (short or mot == -128) else float(mot),
        state=st, axis_err=u32(ae), motor_err=u32(me), enc_err=u32(ee), ctrl_err=u32(ce),
        buttons=buttons, axes=(rx, ry, rz, slider))


def build_report(tm: Telemetry) -> bytes:
    """Inverse de parse_report (tests et mode démo)."""
    hr = lambda v, k, lim=32767: int(max(-lim, min(lim, round(v * k))))
    tt = lambda c: -128 if c is None else int(max(-127, min(127, c)))
    s32 = lambda v: struct.unpack("<i", struct.pack("<I", v & 0xFFFFFFFF))[0]
    ax = tuple(tm.axes) + (0, 0, 0, 0)
    return _HID.pack(REPORT_ID, tm.buttons, tm.pos_raw, hr(tm.vel, 1000), hr(tm.iq, 1000),
                     ax[0], ax[1], ax[2], hr(tm.torque, 1000), ax[3],
                     hr(tm.vbus, 100), hr(tm.ibus, 100), hr(tm.ibrake, 100),
                     tt(tm.fet_c), tt(tm.motor_c), tm.state,
                     s32(tm.axis_err), s32(tm.motor_err), s32(tm.enc_err), s32(tm.ctrl_err))


# ======================================================================
#  États et erreurs (autogen/interfaces.hpp, ODrive 0.5.6)
# ======================================================================
STATES = {
    0: ("UNDEFINED", T("indéfini")),
    1: ("IDLE", T("au repos (moteur libre)")),
    2: ("STARTUP_SEQUENCE", T("séquence de démarrage")),
    3: ("FULL_CALIBRATION_SEQUENCE", T("calibration complète")),
    4: ("MOTOR_CALIBRATION", T("calibration moteur")),
    6: ("ENCODER_INDEX_SEARCH", T("recherche de l'index")),
    7: ("ENCODER_OFFSET_CALIBRATION", T("calage du codeur")),
    8: ("CLOSED_LOOP_CONTROL", T("boucle fermée (actif)")),
    9: ("LOCKIN_SPIN", T("rotation forcée")),
    10: ("ENCODER_DIR_FIND", T("recherche du sens du codeur")),
    11: ("HOMING", T("prise d'origine")),
    12: ("ENCODER_HALL_POLARITY_CALIBRATION", T("calibration Hall (polarité)")),
    13: ("ENCODER_HALL_PHASE_CALIBRATION", T("calibration Hall (phase)")),
}
IDLE, CLOSED_LOOP = 1, 8
CALIBRATING = {2, 3, 4, 6, 7, 9, 10, 11, 12, 13}


def state_text(st: int) -> str:
    n = STATES.get(st)
    return f"{st} · {n[1]}" if n else f"{st} · ?"


ERRORS = {
    "axis": [
        (0x00000001, "INVALID_STATE", T("État demandé impossible maintenant (ex. boucle fermée avant calibration).")),
        (0x00000040, "MOTOR_FAILED", T("Défaut moteur : voir l'erreur moteur.")),
        (0x00000080, "SENSORLESS_ESTIMATOR_FAILED", T("Estimateur sans capteur en défaut.")),
        (0x00000100, "ENCODER_FAILED", T("Défaut codeur : voir l'erreur codeur.")),
        (0x00000200, "CONTROLLER_FAILED", T("Défaut du contrôleur : voir l'erreur contrôleur.")),
        (0x00000800, "WATCHDOG_TIMER_EXPIRED", T("Chien de garde expiré.")),
        (0x00001000, "MIN_ENDSTOP_PRESSED", T("Fin de course mini appuyé.")),
        (0x00002000, "MAX_ENDSTOP_PRESSED", T("Fin de course maxi appuyé.")),
        (0x00004000, "ESTOP_REQUESTED", T("Arrêt d'urgence demandé (CAN).")),
        (0x00020000, "HOMING_WITHOUT_ENDSTOP", T("Prise d'origine sans fin de course.")),
        (0x00040000, "OVER_TEMP", T("Surchauffe : voir l'erreur moteur.")),
        (0x00080000, "UNKNOWN_POSITION", T("Position inconnue.")),
    ],
    "motor": [
        (0x00000001, "PHASE_RESISTANCE_OUT_OF_RANGE",
         T("Résistance de phase hors plage : fil moteur mal serré, ou calibration_current × R > resistance_calib_max_voltage.")),
        (0x00000002, "PHASE_INDUCTANCE_OUT_OF_RANGE", T("Inductance de phase hors plage : vérifie les fils moteur.")),
        (0x00000008, "DRV_FAULT", T("Le driver de grilles (DRV8301) a signalé un défaut.")),
        (0x00000010, "CONTROL_DEADLINE_MISSED", T("Boucle de commande en retard.")),
        (0x00000080, "MODULATION_MAGNITUDE",
         T("Tension du bus insuffisante pour le courant demandé (resistance_calib_max_voltage ≤ moitié de la tension bus).")),
        (0x00000400, "CURRENT_SENSE_SATURATION", T("Mesure de courant saturée : current_lim > requested_current_range.")),
        (0x00001000, "CURRENT_LIMIT_VIOLATION", T("Courant au-delà de current_lim + current_lim_margin.")),
        (0x00010000, "MODULATION_IS_NAN", T("Calcul de modulation invalide.")),
        (0x00020000, "MOTOR_THERMISTOR_OVER_TEMP", T("Thermistance moteur trop chaude.")),
        (0x00040000, "FET_THERMISTOR_OVER_TEMP", T("Transistors de puissance trop chauds.")),
        (0x00080000, "TIMER_UPDATE_MISSED", T("Mise à jour du timer manquée.")),
        (0x00100000, "CURRENT_MEASUREMENT_UNAVAILABLE", T("Mesure de courant indisponible.")),
        (0x00200000, "CONTROLLER_FAILED", T("Le contrôleur de courant (FOC) a échoué.")),
        (0x00400000, "I_BUS_OUT_OF_RANGE", T("Courant bus hors des limites I_bus_hard_min/max.")),
        (0x00800000, "BRAKE_RESISTOR_DISARMED",
         T("Résistance de freinage désarmée : efface les erreurs ou redémarre la carte.")),
        (0x01000000, "SYSTEM_LEVEL", T("Erreur système (tension, courant bus…) : détail dans Réglages › Alimentation.")),
        (0x02000000, "BAD_TIMING", T("Boucle principale désynchronisée.")),
        (0x04000000, "UNKNOWN_PHASE_ESTIMATE",
         T("Position du rotor inconnue : le calage du codeur n'a pas été fait depuis l'allumage.")),
        (0x08000000, "UNKNOWN_PHASE_VEL", T("Vitesse électrique inconnue.")),
        (0x10000000, "UNKNOWN_TORQUE", T("Consigne de couple invalide.")),
        (0x20000000, "UNKNOWN_CURRENT_COMMAND", T("Consigne de courant invalide.")),
        (0x40000000, "UNKNOWN_CURRENT_MEASUREMENT", T("Mesure de courant invalide.")),
        (0x80000000, "UNKNOWN_VBUS_VOLTAGE", T("Tension bus inconnue.")),
    ],
    "encoder": [
        (0x00000001, "UNSTABLE_GAIN", T("Gains du codeur instables (bandwidth).")),
        (0x00000002, "CPR_POLEPAIRS_MISMATCH",
         T("CPR et paires de pôles incohérents : le moteur n'a pas tourné de la distance attendue.")),
        (0x00000004, "NO_RESPONSE", T("Le codeur ne répond pas : A/B, 5 V, GND, résistances de tirage.")),
        (0x00000008, "UNSUPPORTED_ENCODER_MODE", T("Mode de codeur non géré.")),
        (0x00000010, "ILLEGAL_HALL_STATE", T("État Hall impossible.")),
        (0x00000020, "INDEX_NOT_FOUND_YET", T("Index Z pas encore trouvé.")),
        (0x00000040, "ABS_SPI_TIMEOUT", T("Codeur SPI : délai dépassé.")),
        (0x00000080, "ABS_SPI_COM_FAIL", T("Codeur SPI : échec de communication.")),
        (0x00000100, "ABS_SPI_NOT_READY", T("Codeur SPI pas prêt.")),
        (0x00000200, "HALL_NOT_CALIBRATED_YET", T("Capteurs Hall pas encore calibrés.")),
    ],
    "controller": [
        (0x00000001, "OVERSPEED", T("Survitesse : vitesse > vel_limit × vel_limit_tolerance.")),
        (0x00000002, "INVALID_INPUT_MODE", T("Mode d'entrée invalide.")),
        (0x00000004, "UNSTABLE_GAIN", T("Gains instables.")),
        (0x00000008, "INVALID_MIRROR_AXIS", T("Axe miroir invalide.")),
        (0x00000010, "INVALID_LOAD_ENCODER", T("Codeur de charge invalide.")),
        (0x00000020, "INVALID_ESTIMATE", T("Estimation de position/vitesse invalide.")),
        (0x00000040, "INVALID_CIRCULAR_RANGE", T("Plage circulaire invalide.")),
        (0x00000080, "SPINOUT_DETECTED", T("Emballement détecté (puissance mécanique/électrique incohérente).")),
    ],
    "system": [
        (0x00000001, "CONTROL_ITERATION_MISSED", T("Itération de commande manquée.")),
        (0x00000002, "DC_BUS_UNDER_VOLTAGE", T("Tension bus sous le seuil bas (batterie vide ou seuil trop haut).")),
        (0x00000004, "DC_BUS_OVER_VOLTAGE", T("Tension bus au-dessus du seuil haut (freinage, batterie pleine).")),
        (0x00000008, "DC_BUS_OVER_REGEN_CURRENT", T("Trop de courant renvoyé vers l'alimentation.")),
        (0x00000010, "DC_BUS_OVER_CURRENT", T("Trop de courant tiré sur l'alimentation.")),
        (0x00000020, "BRAKE_DEADTIME_VIOLATION", T("Temps mort de la résistance de freinage violé.")),
        (0x00000040, "BRAKE_DUTY_CYCLE_NAN", T("Rapport cyclique de freinage invalide.")),
        (0x00000080, "INVALID_BRAKE_RESISTANCE", T("Valeur de résistance de freinage invalide.")),
    ],
}
ERROR_GROUPS = {"axis": T("Axe"), "motor": T("Moteur"), "encoder": T("Codeur"),
                "controller": T("Contrôleur"), "system": T("Système")}


def decode(group: str, value: int) -> list[tuple[str, str]]:
    out, rest = [], int(value or 0)
    for bit, name, desc in ERRORS.get(group, []):
        if rest & bit:
            out.append((name, desc))
            rest &= ~bit
    if rest:
        out.append((f"0x{rest:08X}", T("Bit d'erreur inconnu.")))
    return out


def errors_of(tm: Telemetry) -> list[tuple[str, str, str]]:
    out = []
    for g, v in (("axis", tm.axis_err), ("motor", tm.motor_err), ("encoder", tm.enc_err),
                 ("controller", tm.ctrl_err)):
        for name, desc in decode(g, v):
            out.append((ERROR_GROUPS[g], name, desc))
    return out


# ======================================================================
#  Catalogue des réglages
# ======================================================================
@dataclass
class Field:
    path: str
    label: str
    kind: str                    # "float" | "int" | "bool" | "enum"
    lo: float = 0
    hi: float = 100
    unit: str = ""
    dec: int = 2
    scale: float = 1.0           # valeur affichée = valeur carte × scale
    items: list = field(default_factory=list)   # enum : [(valeur, libellé)]
    tip: str = ""
    critical: bool = False       # ne s'écrit que moteur au repos (IDLE)
    ro: bool = False
    slider: bool = False
    group: str = ""

    @property
    def store(self) -> str:      # où il est mémorisé : "ffb" (sys.save!) ou "odrive" (ss)
        return "ffb" if is_offb(self.path) else "odrive"

    def parse(self, s: str):
        """Texte renvoyé par la carte → valeur Python (None si illisible)."""
        if s is None:
            return None
        s = s.strip()
        try:
            if self.kind == "bool":
                return 1 if s in ("1", "True", "true") else 0 if s in ("0", "False", "false") else None
            if self.kind in ("int", "enum"):
                return int(float(s))
            return float(s)
        except (ValueError, OverflowError):     # OverflowError : « inf » lu pour un champ entier
            return None

    def fmt(self, v) -> str:
        """Valeur Python → texte à écrire (bools en 0/1 : le firmware lit un entier)."""
        if self.kind == "bool":
            return "1" if v else "0"
        if self.kind in ("int", "enum"):
            return str(int(round(v)))
        if not math.isfinite(v):
            return "inf" if v > 0 else "-inf"
        # pas de notation exponentielle (sscanf « %f » du firmware) ; 9 décimales couvrent les µH
        t = f"{v:.9f}".rstrip("0").rstrip(".")
        return t if t not in ("", "-0") else "0"

    def to_display(self, raw):
        if raw is None or self.kind in ("bool", "enum"):
            return raw
        return raw * self.scale

    def from_display(self, disp):
        if self.kind in ("bool", "enum"):
            return int(disp)
        v = disp / self.scale if self.scale != 1 else disp
        return int(round(v)) if self.kind == "int" else float(v)

    def same(self, a, b) -> bool:
        if a is None or b is None:
            return False
        if self.kind == "float":
            if not (math.isfinite(a) and math.isfinite(b)):
                return a == b
            return abs(a - b) <= max(1e-6, abs(b) * 1e-4, 0.5 * 10 ** (-self.dec) / max(self.scale, 1e-12))
        return int(a) == int(b)


def _f(*a, **k):
    return Field(*a, **k)


MOTOR_TYPES = [(0, T("Courant fort (moteur classique)")), (2, T("Gimbal (régulation en tension)")),
               (3, T("Asynchrone (ACIM)"))]
ENC_MODES = [(0, T("Incrémental A/B")), (1, "Hall"), (2, "Sin/Cos"), (256, "SPI CUI (AMT23)"),
             (257, "SPI AMS (AS5047/AS5048)"), (258, "SPI AEAT"), (259, "SPI RLS"), (260, "SPI MA732"),
             (261, "SPI MT6835")]
CONTROL_MODES = [(0, T("Tension")), (1, T("Couple (obligatoire pour le volant)")), (2, T("Vitesse")),
                 (3, T("Position"))]
INPUT_MODES = [(0, T("Inactif")), (1, T("Direct (passthrough)")), (2, T("Rampe de vitesse")),
               (3, T("Filtre de position")), (5, T("Trajectoire trapèze")), (6, T("Rampe de couple"))]
GPIO_MODES = [(0, T("Désactivé")), (1, T("Bouton")), (2, T("Axe analogique")), (3, T("Recentrage du volant"))]

G = {}  # groupe → titre de carte (rempli plus bas, dans l'ordre d'affichage)


def _grp(key, title):
    G[key] = title
    return key


FFB_RANGE = _grp("ffb_range", T("Course et couple"))
FFB_ALWAYS = _grp("ffb_always", T("Effets permanents (s'ajoutent au jeu)"))
FFB_STOPS = _grp("ffb_stops", T("Butées électroniques"))
FFB_CURVE = _grp("ffb_curve", T("Courbe et lissage du couple"))
FX_GAINS = _grp("fx_gains", T("Gains des effets du jeu"))
FX_FILT = _grp("fx_filt", T("Filtres passe-bas par effet"))
FX_EQ = _grp("fx_eq", T("Égaliseur 3 bandes"))
MOT = _grp("motor", T("Moteur"))
MOT_CAL = _grp("motor_cal", T("Calibration moteur"))
ENC = _grp("encoder", T("Codeur"))
CTRL = _grp("control", T("Contrôle et sécurité vitesse"))
BOOT = _grp("startup", T("Au démarrage de la carte"))
PWR = _grp("power", T("Alimentation et protections"))
BRAKE = _grp("brake", T("Résistance de freinage"))
TEMP = _grp("temp", T("Température de la carte"))

FIELDS: list[Field] = [
    # ---------------------------------------------------------------- volant (FFB)
    _f("axis.range", T("Course totale"), "int", 90, 3600, "°", slider=True, group=FFB_RANGE,
       tip=T("Angle total de butée à butée (900° = 450° de chaque côté). Les jeux le règlent souvent eux-mêmes.")),
    _f("axis.maxtorque", T("Couple maximum"), "float", 0.1, 40, "N·m", 2, slider=True, group=FFB_RANGE,
       tip=T("Couple qui correspond à 100 % de force du jeu. Plafonné à 40 N·m par le firmware. Commence bas "
             "(3 N·m) et monte par paliers.")),
    _f("axis.fxratio", T("Force globale"), "float", 0, 100, "%", 0, scale=100, slider=True, group=FFB_RANGE,
       tip=T("Atténuateur général des effets du jeu. Baisse-le si le couple sature (clipping).")),
    _f("axis.invert", T("Inverser le sens du volant (position)"), "bool", group=FFB_RANGE,
       tip=T("Inverse la position envoyée au jeu ET le sens des forces du jeu.")),
    _f("axis.ffbinvert", T("Inverser uniquement les forces du jeu"), "bool", group=FFB_RANGE,
       tip=T("Pour les jeux ou outils qui envoient la force avec le mauvais signe.")),
    _f("axis.idlespring", T("Ressort au repos (hors jeu)"), "int", 0, 255, "", slider=True, group=FFB_ALWAYS,
       tip=T("Ressort de centrage quand aucun jeu n'envoie de force.")),
    _f("axis.axisdamper", T("Amortissement permanent"), "int", 0, 255, "", slider=True, group=FFB_ALWAYS,
       tip=T("Freinage proportionnel à la vitesse, toujours actif. Stabilise un volant qui oscille.")),
    _f("axis.axisfriction", T("Frottement permanent"), "int", 0, 255, "", slider=True, group=FFB_ALWAYS),
    _f("axis.axisinertia", T("Inertie permanente"), "int", 0, 255, "", slider=True, group=FFB_ALWAYS),
    _f("axis.esgain", T("Raideur des butées"), "int", 0, 255, "", slider=True, group=FFB_STOPS,
       tip=T("Force du ressort qui bloque le volant en bout de course.")),
    _f("axis.esdamp", T("Amortissement des butées"), "int", 0, 255, "", slider=True, group=FFB_STOPS,
       tip=T("Évite le rebond contre la butée.")),
    _f("axis.maxtorquerate", T("Limite de variation du couple"), "int", 0, 65535, T("pts/ms"), group=FFB_CURVE,
       tip=T("Variation maximale du couple par milliseconde, en points internes (32767 = couple maximum). "
             "0 = pas de limite.")),
    _f("axis.expo", T("Courbe exponentielle"), "int", -32767, 32767, "", group=FFB_CURVE,
       tip=T("0 = linéaire. Positif : plus de détail sur les petites forces.")),
    _f("axis.exposcale", T("Échelle de la courbe"), "int", 1, 255, "", group=FFB_CURVE),
    # ---------------------------------------------------------------- effets du jeu
    _f("fx.master", T("Gain général"), "int", 0, 255, "", slider=True, group=FX_GAINS,
       tip=T("255 = 100 %. Le jeu peut aussi le modifier.")),
    _f("fx.spring", T("Ressort"), "int", 0, 255, "", slider=True, group=FX_GAINS),
    _f("fx.damper", T("Amortissement"), "int", 0, 255, "", slider=True, group=FX_GAINS),
    _f("fx.friction", T("Frottement"), "int", 0, 255, "", slider=True, group=FX_GAINS),
    _f("fx.inertia", T("Inertie"), "int", 0, 255, "", slider=True, group=FX_GAINS),
    _f("fx.filterCfFreq", T("Force constante : coupure"), "int", 1, 500, "Hz", group=FX_FILT,
       tip=T("Le filtre le plus important : plus bas = plus doux, plus haut = plus de détails (bordures).")),
    _f("fx.filterCfQ", T("Force constante : Q"), "int", 0.01, 5, "", 2, scale=0.01, group=FX_FILT),
    _f("fx.filterFrFreq", T("Frottement : coupure"), "int", 1, 500, "Hz", group=FX_FILT),
    _f("fx.filterFrQ", T("Frottement : Q"), "int", 0.01, 5, "", 2, scale=0.01, group=FX_FILT),
    _f("fx.filterDaFreq", T("Amortissement : coupure"), "int", 1, 500, "Hz", group=FX_FILT),
    _f("fx.filterDaQ", T("Amortissement : Q"), "int", 0.01, 5, "", 2, scale=0.01, group=FX_FILT),
    _f("fx.filterInFreq", T("Inertie : coupure"), "int", 1, 500, "Hz", group=FX_FILT),
    _f("fx.filterInQ", T("Inertie : Q"), "int", 0.01, 5, "", 2, scale=0.01, group=FX_FILT),
    _f("axis.eqweight", T("Poids (5 Hz)"), "float", -12, 12, "dB", 1, slider=True, group=FX_EQ,
       tip=T("Le couple constant en virage ne change jamais. Monter « Poids » réduit le reste par contraste.")),
    _f("axis.eqchassis", T("Châssis (12 Hz)"), "float", -12, 12, "dB", 1, slider=True, group=FX_EQ),
    _f("axis.eqroad", T("Route (25 Hz)"), "float", -12, 12, "dB", 1, slider=True, group=FX_EQ,
       tip=T("Monter « Route » fait ressortir bordures et texture de la piste.")),
    # ---------------------------------------------------------------- moteur
    _f("axis0.motor.config.motor_type", T("Type de moteur"), "enum", items=MOTOR_TYPES, critical=True, group=MOT),
    _f("axis0.motor.config.pole_pairs", T("Paires de pôles"), "int", 1, 60, "", critical=True, group=MOT,
       tip=T("Nombre d'aimants ÷ 2. Moteur de hoverboard : souvent 15. Une valeur fausse fait échouer le calage.")),
    _f("axis0.motor.config.torque_constant", T("Constante de couple Kt"), "float", 0.001, 20, "N·m/A", 4,
       group=MOT, tip=T("Kt ≈ 8,27 / KV. Sert à convertir le couple demandé en courant.")),
    _f("axis0.motor.config.current_lim", T("Courant maximum"), "float", 0.5, 80, "A", 1, slider=True, group=MOT,
       tip=T("Plafond réel du couple : couple maxi ≈ Kt × courant maxi. Commence à 10 A.")),
    _f("axis0.motor.config.current_lim_margin", T("Marge avant défaut de courant"), "float", 0, 40, "A", 1,
       group=MOT),
    _f("axis0.motor.config.requested_current_range", T("Gamme de mesure du courant"), "float", 1, 120, "A", 0,
       critical=True, group=MOT, tip=T("Doit rester au-dessus du courant maximum. Pris en compte au redémarrage.")),
    _f("axis0.motor.config.current_control_bandwidth", T("Bande passante de la boucle de courant"), "float",
       10, 10000, "rad/s", 0, group=MOT,
       tip=T("Plus haut = réponse plus nette mais plus de bruit moteur. 1000 par défaut, souvent 200–1000 sur "
             "un moteur de hoverboard.")),
    _f("axis0.motor.config.calibration_current", T("Courant de calibration"), "float", 0.5, 40, "A", 1,
       critical=True, group=MOT_CAL),
    _f("axis0.motor.config.resistance_calib_max_voltage", T("Tension max de calibration"), "float", 0.5, 30, "V",
       1, critical=True, group=MOT_CAL,
       tip=T("Doit dépasser courant de calibration × résistance, et rester sous la moitié de la tension bus.")),
    _f("axis0.motor.config.phase_resistance", T("Résistance de phase mesurée"), "float", 0, 100, "Ω", 4, ro=True,
       group=MOT_CAL),
    _f("axis0.motor.config.phase_inductance", T("Inductance de phase mesurée"), "float", 0, 1e5, "µH", 1,
       scale=1e6, ro=True, group=MOT_CAL),
    _f("axis0.motor.config.pre_calibrated", T("Moteur déjà calibré (ne pas refaire au démarrage)"), "bool",
       critical=True, group=MOT_CAL),
    # ---------------------------------------------------------------- codeur
    _f("axis0.encoder.config.mode", T("Type de codeur"), "enum", items=ENC_MODES, critical=True, group=ENC),
    _f("axis0.encoder.config.cpr", T("Points par tour moteur (CPR)"), "int", 1, 2000000, "", critical=True,
       group=ENC, tip=T("Incrémental : PPR × 4 × rapport de transmission. Ex. codeur 2500 PPR, courroie 72/16 : 2500 × 4 × 72/16 = 45000.")),
    _f("axis0.encoder.config.use_index", T("Utiliser l'index Z"), "bool", critical=True, group=ENC,
       tip=T("À laisser décoché si le codeur est entraîné par courroie avec un rapport non entier.")),
    _f("axis0.encoder.config.direction", T("Sens du codeur (trouvé à la calibration)"), "int", -1, 1, "",
       critical=True, group=ENC),
    _f("axis0.encoder.config.pre_calibrated", T("Calage codeur conservé (index ou absolu uniquement)"), "bool",
       critical=True, group=ENC,
       tip=T("Ne coche PAS avec un codeur incrémental sans index : le calage serait faux au prochain allumage.")),
    _f("axis0.encoder.config.bandwidth", T("Bande passante du codeur (PLL)"), "float", 10, 20000, "rad/s", 0,
       group=ENC, tip=T("Lissage de la vitesse estimée, utilisée par l'amortissement, le frottement et l'inertie.")),
    _f("axis0.encoder.config.calib_range", T("Tolérance de la calibration"), "float", 0.001, 1, "", 3,
       critical=True, group=ENC),
    _f("axis0.controller.config.control_mode", T("Mode de commande"), "enum", items=CONTROL_MODES, critical=True,
       group=CTRL, tip=T("Le volant fonctionne en commande de couple.")),
    _f("axis0.controller.config.input_mode", T("Mode d'entrée"), "enum", items=INPUT_MODES, critical=True,
       group=CTRL),
    _f("axis0.controller.config.vel_limit", T("Vitesse maxi (anti-emballement)"), "float", 0.1, 200, "tr/s", 2,
       group=CTRL, tip=T("Au-delà, le couple est réduit ; × tolérance, la carte coupe avec une erreur de survitesse.")),
    _f("axis0.controller.config.vel_limit_tolerance", T("Tolérance de survitesse"), "float", 1, 10, "×", 2,
       group=CTRL),
    _f("axis0.controller.config.enable_torque_mode_vel_limit", T("Limiter la vitesse en mode couple"), "bool",
       group=CTRL),
    _f("axis0.controller.config.enable_overspeed_error", T("Couper en cas de survitesse"), "bool", group=CTRL),
    _f("axis0.controller.config.vel_gain", T("Gain de vitesse (limitation)"), "float", 0, 50, "N·m/(tr/s)", 4,
       group=CTRL, tip=T("Utilisé seulement pour freiner au-delà de la vitesse maxi.")),
    _f("axis0.config.startup_motor_calibration", T("Calibrer le moteur"), "bool", critical=True, group=BOOT),
    _f("axis0.config.startup_encoder_index_search", T("Chercher l'index Z"), "bool", critical=True, group=BOOT),
    _f("axis0.config.startup_encoder_offset_calibration", T("Caler le codeur (le volant bouge ~1 tour)"), "bool",
       critical=True, group=BOOT,
       tip=T("Indispensable avec un codeur incrémental sans index.")),
    _f("axis0.config.startup_closed_loop_control", T("Passer en boucle fermée"), "bool", critical=True, group=BOOT),
    # ---------------------------------------------------------------- alimentation
    _f("sys.vbusdiv", T("Rapport du pont diviseur de tension"), "int", 1, 50, "", critical=True, group=PWR,
       tip=T("19 sur ODrive v3.6-56V et MKS, 11 sur la version 24 V. Toutes les protections en dépendent.")),
    _f("config.dc_bus_overvoltage_trip_level", T("Coupure tension haute"), "float", 5, 60, "V", 1, critical=True,
       group=PWR, tip=T("Ex. batterie 10S (42 V pleine) : 46 V.")),
    _f("config.dc_bus_undervoltage_trip_level", T("Coupure tension basse"), "float", 5, 60, "V", 1, critical=True,
       group=PWR, tip=T("Ex. batterie 10S : 32 V (3,2 V par cellule).")),
    _f("config.dc_max_positive_current", T("Courant maxi tiré sur l'alimentation"), "float", 0, 120, "A", 1,
       critical=True, group=PWR),
    _f("config.dc_max_negative_current", T("Courant maxi renvoyé vers l'alimentation"), "float", -120, 0, "A", 1,
       critical=True, group=PWR),
    _f("config.max_regen_current", T("Courant de récupération autorisé"), "float", 0, 60, "A", 1, critical=True,
       group=PWR, tip=T("0 = tout le freinage part dans la résistance.")),
    _f("config.enable_brake_resistor", T("Résistance de freinage branchée"), "bool", critical=True, group=BRAKE),
    _f("config.brake_resistance", T("Valeur de la résistance"), "float", 0.1, 100, "Ω", 2, critical=True,
       group=BRAKE, tip=T("Valeur exacte gravée sur la résistance (ex. 2 Ω).")),
    # (motor.config.inverter_temp_limit_* existe encore dans l'interface 0.5.6 mais n'est plus utilisé)
    _f("axis0.motor.fet_thermistor.config.enabled", T("Protection thermique des transistors"), "bool", group=TEMP),
    _f("axis0.motor.fet_thermistor.config.temp_limit_lower", T("Début de réduction du courant"), "float", 20, 150,
       "°C", 0, group=TEMP),
    _f("axis0.motor.fet_thermistor.config.temp_limit_upper", T("Coupure"), "float", 20, 150, "°C", 0, group=TEMP),
]
BY_PATH = {f.path: f for f in FIELDS}

# Réglages masqués par défaut (case « Réglages avancés ») : utiles rarement, valeurs d'usine correctes
ADVANCED = {
    "axis.maxtorquerate", "axis.expo", "axis.exposcale",
    "fx.filterCfQ", "fx.filterFrFreq", "fx.filterFrQ", "fx.filterDaFreq", "fx.filterDaQ", "fx.filterInFreq",
    "fx.filterInQ", "axis.eqweight", "axis.eqchassis", "axis.eqroad",
    "axis0.motor.config.motor_type", "axis0.motor.config.current_lim_margin",
    "axis0.motor.config.requested_current_range", "axis0.motor.config.current_control_bandwidth",
    "axis0.motor.config.resistance_calib_max_voltage", "axis0.encoder.config.bandwidth",
    "axis0.encoder.config.calib_range", "axis0.controller.config.control_mode",
    "axis0.controller.config.input_mode", "axis0.controller.config.vel_limit_tolerance",
    "axis0.controller.config.enable_torque_mode_vel_limit", "axis0.controller.config.vel_gain",
    "axis0.config.startup_encoder_index_search", "axis0.motor.fet_thermistor.config.enabled",
    "axis0.motor.fet_thermistor.config.temp_limit_lower", "axis0.motor.fet_thermistor.config.temp_limit_upper",
}

# lectures en direct (pas des réglages)
EQ_INFO = ["axis.eqweightfreq", "axis.eqchassisfreq", "axis.eqroadfreq",
           "axis.eqweightq", "axis.eqchassisq", "axis.eqroadq"]
IDENTITY = ["hw_version_major", "hw_version_minor", "hw_version_variant", "fw_version_major",
            "fw_version_minor", "fw_version_revision", "serial_number", "sys.hwtype", "sys.uid",
            "axis.zeroofs", "error"]

# GPIO (gpio.<n>.<champ>) : 1-4 et 6 ; seuls 1-4 ont un convertisseur analogique
GPIO_PINS = [1, 2, 3, 4, 6]
GPIO_ANALOG = {1, 2, 3, 4}
GPIO_FIELDS = ["mode", "idx", "invert", "amin", "amax"]
GPIO_GLOBAL = [
    _f("axis.gpiofilt", T("Filtre passe-bas sur les axes GPIO"), "bool"),
    _f("axis.gpiofiltf", T("Coupure du filtre"), "float", 0.5, 500, "Hz", 1),
    _f("axis.gpioautocal", T("Calibration automatique mini/maxi"), "bool"),
]
for _g in GPIO_GLOBAL:
    BY_PATH[_g.path] = _g


def gpio_field(pin: int, name: str) -> Field:
    p = f"gpio.{pin}.{name}"
    f = BY_PATH.get(p)
    if f:
        return f
    if name == "mode":
        items = GPIO_MODES if pin in GPIO_ANALOG else [m for m in GPIO_MODES if m[0] != 2]
        f = Field(p, T("Mode"), "enum", items=items)
    elif name == "idx":
        f = Field(p, T("N° bouton / axe"), "int", 0, 63)
    elif name == "invert":
        f = Field(p, T("Inverser"), "bool")
    else:
        f = Field(p, T("Mini") if name == "amin" else T("Maxi"), "int", 0, 4095)
    BY_PATH[p] = f
    return f


for _p in GPIO_PINS:
    for _n in GPIO_FIELDS:
        gpio_field(_p, _n)

# Odrive ASCII : réponses d'erreur possibles
ASCII_ERRORS = ("invalid property", "not implemented", "invalid command format", "unknown command",
                "invalid motor")
