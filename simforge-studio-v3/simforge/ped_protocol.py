"""
Protocole série des pédales actives DIY de ChrGri (DIY-Sim-Racing-FFB-Pedal), écrit à partir de leur code source.

Licence de ce module : il reprend les structures de données du projet ChrGri, sous Creative Commons BY-NC-SA 4.0
(attribution : ChrGri et contributeurs, https://github.com/ChrGri/DIY-Sim-Racing-FFB-Pedal). Usage non commercial.

Trame (identique dans les deux sens) :
    en-tête 6 octets  : 0xAA 0x55 | type | version | mémoriser (0/1) | n° de pédale
    charge utile      : structure « packed » (little-endian) selon le type
    pied 4 octets     : somme de Fletcher-16 sur en-tête + charge utile | 0xAA 0x56
Types : 100 configuration, 110 action, 120 état de base (envoyé en continu), 130 état détaillé (si activé).
Liaison : port série USB de l'ESP32-S3 (puce CH343/CP210x de la carte), 3 000 000 bauds, DTR/RTS au repos
(sinon l'ESP32 redémarre à l'ouverture du port).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .i18n import T
from .ped_layout import CONFIG_FIELDS, STATE_BASIC_FIELDS, STATE_EXT_FIELDS, ACTION_FIELDS

# version de structure attendue par le firmware livré avec SimForge (PedalDefine.h)
VERSION = 174
BAUD = 3_000_000

SOF = b"\xAA\x55"
EOF_ = b"\xAA\x56"
T_CONFIG, T_ACTION, T_STATE, T_STATE_EXT = 100, 110, 120, 130
T_BRIDGE_STATE = 210

HEADER = struct.Struct("<BBBBBB")
FOOTER = struct.Struct("<HBB")


def _fmt(fields):
    return "<" + "".join((str(c) if c > 1 else "") + t for _n, t, c in fields)


CONFIG_S = struct.Struct(_fmt(CONFIG_FIELDS))
STATE_S = struct.Struct(_fmt(STATE_BASIC_FIELDS))
STATE_EXT_S = struct.Struct(_fmt(STATE_EXT_FIELDS))
ACTION_S = struct.Struct(_fmt(ACTION_FIELDS))
SIZES = {T_CONFIG: CONFIG_S.size, T_ACTION: ACTION_S.size, T_STATE: STATE_S.size, T_STATE_EXT: STATE_EXT_S.size}
FRAME_SIZES = {k: HEADER.size + v + FOOTER.size for k, v in SIZES.items()}
CONFIG_NAMES = [n for n, _t, _c in CONFIG_FIELDS]


def fletcher16(data: bytes) -> int:
    s1 = s2 = 0
    for b in data:
        s1 += b
        s2 += s1
    return ((s2 % 255) << 8) | (s1 % 255)


def frame(ptype: int, payload: bytes, store=0, tag=0, version=VERSION) -> bytes:
    head = HEADER.pack(0xAA, 0x55, ptype, version, 1 if store else 0, tag & 0xFF)
    crc = fletcher16(head + payload)
    return head + payload + FOOTER.pack(crc, 0xAA, 0x56)


def _unpack(fields, s, payload):
    vals = s.unpack(payload)
    out, i = {}, 0
    for n, _t, c in fields:
        if c == 1:
            out[n] = vals[i]
            i += 1
        else:
            out[n] = list(vals[i:i + c])
            i += c
    return out


def _pack(fields, s, d):
    vals = []
    for n, _t, c in fields:
        v = d[n]
        if c == 1:
            vals.append(v)
        else:
            vals.extend(v)
    return s.pack(*vals)


@dataclass
class Frame:
    ptype: int
    version: int
    store: int
    tag: int
    data: dict
    raw: bytes = b""


class Parser:
    """Découpe le flux série (trames binaires mêlées aux messages texte du firmware)."""

    def __init__(self):
        self.buf = bytearray()
        self.text = bytearray()
        self.bad_crc = 0
        self.lines: list[str] = []

    def feed(self, data: bytes) -> list[Frame]:
        self.buf += data
        out = []
        while True:
            i = self.buf.find(SOF)
            if i < 0:
                keep = 1 if self.buf.endswith(b"\xAA") else 0
                self._text(bytes(self.buf[:len(self.buf) - keep]))
                del self.buf[:len(self.buf) - keep]
                break
            if i:
                self._text(bytes(self.buf[:i]))
                del self.buf[:i]
            if len(self.buf) < 6:
                break
            ptype, version = self.buf[2], self.buf[3]
            size = FRAME_SIZES.get(ptype)
            if size is None:
                del self.buf[:1]            # type inconnu : ce n'était pas un début de trame
                continue
            if len(self.buf) < size:
                break
            pkt = bytes(self.buf[:size])
            if pkt[-2:] != EOF_:
                del self.buf[:1]
                continue
            crc = struct.unpack_from("<H", pkt, size - 4)[0]
            if crc != fletcher16(pkt[:size - 4]):
                self.bad_crc += 1
                del self.buf[:1]
                continue
            del self.buf[:size]
            payload = pkt[6:size - 4]
            data = {}
            if version == VERSION:
                if ptype == T_CONFIG:
                    data = _unpack(CONFIG_FIELDS, CONFIG_S, payload)
                elif ptype == T_STATE:
                    data = _unpack(STATE_BASIC_FIELDS, STATE_S, payload)
                elif ptype == T_STATE_EXT:
                    data = _unpack(STATE_EXT_FIELDS, STATE_EXT_S, payload)
                elif ptype == T_ACTION:
                    data = _unpack(ACTION_FIELDS, ACTION_S, payload)
            out.append(Frame(ptype, version, pkt[4], pkt[5], data, pkt))
        return out

    def _text(self, b: bytes):
        if not b:
            return
        self.text += b
        while b"\n" in self.text:
            line, _, rest = bytes(self.text).partition(b"\n")
            self.text = bytearray(rest)
            s = line.decode("latin-1", "replace").strip("\r ")
            if s and sum(32 <= ord(ch) < 127 for ch in s) > len(s) * 0.8:
                self.lines.append(s)
        if len(self.text) > 600:
            self.text.clear()


def build_config(cfg: dict, store=False, tag=0) -> bytes:
    return frame(T_CONFIG, _pack(CONFIG_FIELDS, CONFIG_S, cfg), store, tag)


def build_action(tag=0, **kw) -> bytes:
    d = {n: 0 for n, _t, _c in ACTION_FIELDS}
    d.update(kw)
    return frame(T_ACTION, _pack(ACTION_FIELDS, ACTION_S, d), 0, tag)


# actions système (PedalEnum.h : PedalSystemAction)
ACT_RESTART = 2
ACT_DOWNLOAD_MODE = 5
ACT_PRINT_INFO = 6
ACT_BEEP = 11
ACT_WAKEUP = 12

PEDAL_NAMES = {0: T("Embrayage"), 1: T("Frein"), 2: T("Accélérateur"), 3: T("Erreur d'assignation"),
               4: T("Non assignée")}
SERVO_STATUS = {0: T("servo non connecté"), 1: T("servo connecté"), 2: T("servo en veille"), 3: T("servo arrêté")}
PEDAL_STATUS = {0: T("normal"), 1: T("palonnier"), 2: T("palonnier + frein")}
ERROR_CODES = {12: T("le servo ne répond plus (liaison série du servo)"),
               101: T("ESP-NOW : charge utile invalide"), 102: T("ESP-NOW : version différente"),
               103: T("ESP-NOW : CRC faux"), 111: T("ESP-NOW : charge utile invalide"),
               112: T("ESP-NOW : version différente"), 113: T("ESP-NOW : CRC faux")}


def plausible(c: dict) -> list[str]:
    """Mêmes contrôles que le firmware (isPedalConfigPlausible) : une config refusée par la pédale serait ignorée."""
    e = []
    if not 1 <= c["spindlePitch_mmPerRev_u8"] <= 20:
        e.append(T("pas de la vis entre 1 et 20 mm"))
    if not 10 <= c["lengthPedalTravel_i16"] <= 200:
        e.append(T("course de la pédale entre 10 et 200 mm"))
    if c["pedalStartPosition_u8"] >= 100 or c["pedalEndPosition_u8"] > 100:
        e.append(T("positions de début/fin entre 0 et 100 %"))
    if c["pedalEndPosition_u8"] - c["pedalStartPosition_u8"] < 5:
        e.append(T("la fin doit dépasser le début d'au moins 5 %"))
    rudder = c["relativeForce01_u8"] == 1 or c["preloadForce_fl32"] < 0
    if not rudder:
        if not 1 <= c["maxForce_fl32"] <= 500:
            e.append(T("force maxi entre 1 et 500 kg"))
        if not 0 <= c["preloadForce_fl32"] < c["maxForce_fl32"]:
            e.append(T("précharge entre 0 et la force maxi"))
    if c["loadcellRating_u8"] < 10:
        e.append(T("capacité du capteur de force ≥ 20 kg"))
    for k, lo, hi in (("lengthPedalA_i16", 50, 500), ("lengthPedalB_i16", 50, 500),
                      ("lengthPedalCHorizontal_i16", 50, 500), ("lengthPedalD_i16", -300, 300)):
        if not lo <= c[k] <= hi:
            e.append(T("cote {k} entre {lo} et {hi} mm").format(k=k.replace("lengthPedal", "").replace("_i16", ""),
                                                                lo=lo, hi=hi))
    if c["pedalType_u8"] > 4:
        e.append(T("rôle de pédale invalide"))
    return e


# ======================================================================
#  Catalogue des réglages affichés
# ======================================================================
@dataclass
class PField:
    name: str
    label: str
    kind: str = "int"        # int | float | bool | enum
    lo: float = 0
    hi: float = 255
    unit: str = ""
    scale: float = 1.0       # affiché = brut × scale
    dec: int = 0
    items: list = field(default_factory=list)
    tip: str = ""
    adv: bool = False
    group: str = ""


G_MAIN = T("Pédale")
G_FX = T("Effets (ABS, régime, point de patinage…)")
G_MECH = T("Mécanique de la pédale")
G_CTRL = T("Régulation et servo")

PFIELDS = [
    PField("pedalType_u8", T("Rôle de la pédale"), "enum",
           items=[(0, T("Embrayage")), (1, T("Frein")), (2, T("Accélérateur"))], group=G_MAIN,
           tip=T("Choisit l'axe de manette et les effets reçus.")),
    PField("pedalStartPosition_u8", T("Début de course"), lo=0, hi=99, unit="%", group=G_MAIN,
           tip=T("Position de repos de la pédale, en % de la course mécanique.")),
    PField("pedalEndPosition_u8", T("Fin de course"), lo=1, hi=100, unit="%", group=G_MAIN),
    PField("preloadForce_fl32", T("Précharge (force au repos)"), "float", 0, 100, "kg", dec=1, group=G_MAIN),
    PField("maxForce_fl32", T("Force maximum"), "float", 1, 500, "kg", dec=1, group=G_MAIN,
           tip=T("Force à fond de course (frein : souvent 40 à 80 kg avec un capteur de 100 kg).")),
    PField("maxGameOutput_u8", T("Sortie maxi vers le jeu"), lo=1, hi=100, unit="%", group=G_MAIN,
           tip=T("100 % = le jeu reçoit 100 % à la force maximum.")),
    PField("travelAsJoystickOutput_u8", T("Axe envoyé au jeu"), "enum",
           items=[(0, T("Force (frein à capteur)")), (1, T("Position (course)"))], group=G_MAIN),
    PField("simulateAbsTrigger_u8", T("ABS simulé (sans jeu)"), "bool", group=G_FX,
           tip=T("La pédale vibre toute seule au-delà du seuil : pratique pour régler l'ABS hors jeu.")),
    PField("simulateAbsValue_u8", T("Seuil de l'ABS simulé"), lo=0, hi=100, unit="%", group=G_FX),
    PField("absFrequency_u8", T("Fréquence de l'ABS"), lo=1, hi=255, unit="Hz", group=G_FX),
    PField("absAmplitude_u8", T("Amplitude de l'ABS"), group=G_FX, tip=T("Valeur brute du firmware (0–255).")),
    PField("absPattern_u8", T("Forme de l'ABS"), "enum", items=[(0, T("Sinus")), (1, T("Dent de scie"))],
           group=G_FX),
    PField("absForceOrTarvelBit_u8", T("L'ABS agit sur"), "enum", items=[(0, T("la force")), (1, T("la course"))],
           group=G_FX),
    PField("rpmMinFreq_u8", T("Régime : fréquence mini"), unit="Hz", group=G_FX, adv=True),
    PField("rpmMaxFreq_u8", T("Régime : fréquence maxi"), unit="Hz", group=G_FX, adv=True),
    PField("rpmAmp_u8", T("Régime : amplitude"), group=G_FX, adv=True, tip=T("Valeur brute du firmware.")),
    PField("bpTriggerValue_u8", T("Point de patinage : position"), unit="%", hi=100, group=G_FX, adv=True),
    PField("bpAmp_u8", T("Point de patinage : amplitude"), group=G_FX, adv=True),
    PField("bpFreq_u8", T("Point de patinage : fréquence"), unit="Hz", group=G_FX, adv=True),
    PField("wsAmp_u8", T("Patinage des roues : amplitude"), group=G_FX, adv=True),
    PField("wsFreq_u8", T("Patinage des roues : fréquence"), unit="Hz", group=G_FX, adv=True),
    PField("gMulti_u8", T("Effet G : multiplicateur"), unit="%", group=G_FX, adv=True),
    PField("roadMulti_u8", T("Chocs de la route : multiplicateur"), unit="%", group=G_FX, adv=True),
    PField("lengthPedalTravel_i16", T("Course mécanique"), lo=10, hi=200, unit="mm", group=G_MECH),
    PField("lengthPedalA_i16", T("Cote A"), lo=50, hi=500, unit="mm", group=G_MECH),
    PField("lengthPedalB_i16", T("Cote B"), lo=50, hi=500, unit="mm", group=G_MECH),
    PField("lengthPedalCHorizontal_i16", T("Cote C horizontale"), lo=50, hi=500, unit="mm", group=G_MECH),
    PField("lengthPedalCVertical_i16", T("Cote C verticale"), lo=-500, hi=500, unit="mm", group=G_MECH),
    PField("lengthPedalD_i16", T("Cote D"), lo=-300, hi=300, unit="mm", group=G_MECH),
    PField("spindlePitch_mmPerRev_u8", T("Pas de la vis à billes"), lo=1, hi=20, unit=T("mm/tr"), group=G_MECH),
    PField("loadcellRating_u8", T("Capacité du capteur de force"), lo=20, hi=510, unit="kg", scale=2, group=G_MECH,
           tip=T("Valeur écrite sur le capteur (ex. 100 kg).")),
    PField("invertLoadcellReading_u8", T("Inverser le capteur de force"), "bool", group=G_MECH),
    PField("invertMotorDirection_u8", T("Inverser le sens du moteur"), "bool", group=G_MECH),
    PField("enableBrakeResistor_u8", T("Énergie de freinage du servo"), "enum",
           items=[(0, T("résistance interne du servo")), (1, T("+ résistance externe pilotée")),
                  (2, T("circuit matériel seul"))], group=G_CTRL),
    PField("brakeResistorResistance_Ohm_u8", T("Valeur de la résistance externe"), lo=0, hi=255, unit="Ω",
           group=G_CTRL, tip=T("0 = 10 Ω par défaut.")),
    PField("servoIdleTimeout_u8", T("Mise en veille du servo"), group=G_CTRL, adv=True,
           tip=T("Valeur brute du firmware ; 0 = jamais.")),
    PField("wakeOnPluginOnly_u8", T("Au démarrage"), "enum",
           items=[(0, T("la pédale démarre seule")), (1, T("attend le logiciel (veille)"))], group=G_CTRL),
    PField("virtualPedalMassInPercent_u8", T("Masse virtuelle"), unit="%", group=G_CTRL, adv=True),
    PField("virtualPedalDampingInPercent_u8", T("Amortissement virtuel"), unit="%", group=G_CTRL, adv=True),
    PField("dampingProgression_u8", T("Progressivité de l'amortissement"), hi=100, unit="%", group=G_CTRL, adv=True),
    PField("coulombFrictionIn0p1N_u8", T("Frottement simulé"), unit="N", scale=0.1, dec=1, group=G_CTRL, adv=True),
    PField("endstopStiffness_kg_mm_u8", T("Raideur de la butée"), unit="kg/mm", group=G_CTRL, adv=True),
    PField("endstopTravelRange_mm_u8", T("Zone de la butée"), unit="mm", group=G_CTRL, adv=True),
    PField("kfModelNoise_u8", T("Filtre de force (Kalman) : bruit du modèle"), group=G_CTRL, adv=True),
    PField("kfModelOrder_u8", T("Filtre de force : ordre du modèle"), group=G_CTRL, adv=True),
    PField("kfJoystick_u8", T("Filtre de l'axe de jeu"), group=G_CTRL, adv=True),
    PField("kfModelNoiseJoystick_u8", T("Filtre de l'axe de jeu : bruit"), group=G_CTRL, adv=True),
    PField("minForceForEffects_u8", T("Force mini pour les effets"), group=G_CTRL, adv=True),
    PField("stepLossFunctionFlags_u8", T("Détection de pas perdus (drapeaux)"), group=G_CTRL, adv=True),
    PField("endstopDetectionThreshold_u8", T("Seuil de détection des butées"), lo=10, hi=50, group=G_CTRL, adv=True),
    PField("debugFlags0_u8", T("Drapeaux de débogage"), group=G_CTRL, adv=True),
]
PBY = {f.name: f for f in PFIELDS}
for _f in PFIELDS:
    assert _f.name in CONFIG_NAMES, _f.name

CURVE_FORCE = [f"relativeForce{i:02d}_u8" for i in range(11)]
CURVE_TRAVEL = [f"relativeTravel{i:02d}_u8" for i in range(11)]
JOY_ORIG = [f"joystickMapOrig{i:02d}_u8" for i in range(11)]
JOY_MAP = [f"joystickMapMapped{i:02d}_u8" for i in range(11)]


def default_config() -> dict:
    """Valeurs d'usine du firmware (DapConfig_t::initializeDefaults) pour la démo et les tests."""
    c = {n: (0 if c == 1 else [0] * c) for n, _t, c in CONFIG_FIELDS}
    c.update(pedalStartPosition_u8=10, pedalEndPosition_u8=85, maxForce_fl32=60.0, preloadForce_fl32=2.0,
             quantityOfControl_u8=6, numOfJoystickMapControl_u8=6, numOfJoystickMapControlToe_u8=6,
             absFrequency_u8=15, lengthPedalA_i16=205, lengthPedalB_i16=220, lengthPedalD_i16=60,
             lengthPedalCHorizontal_i16=215, lengthPedalCVertical_i16=60, lengthPedalTravel_i16=100,
             spindlePitch_mmPerRev_u8=5, simulateAbsValue_u8=80, rpmMaxFreq_u8=40, rpmMinFreq_u8=10, rpmAmp_u8=5,
             bpTriggerValue_u8=50, bpAmp_u8=1, bpFreq_u8=15, gMulti_u8=50, gWindow_u8=60, wsAmp_u8=1, wsFreq_u8=15,
             roadMulti_u8=50, roadWindow_u8=60, maxGameOutput_u8=100, kfModelNoise_u8=255, loadcellRating_u8=50,
             pedalType_u8=1, configHash_u32=175245064)
    for i, v in enumerate((0, 20, 40, 60, 80, 100)):
        for k in (CURVE_FORCE, CURVE_TRAVEL, JOY_ORIG, JOY_MAP):
            c[k[i]] = v
        c[f"joystickMapOrigToe{i:02d}_u8"] = v
        c[f"joystickMapMappedToe{i:02d}_u8"] = v
    return c
