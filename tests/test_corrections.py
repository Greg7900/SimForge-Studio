"""Comportements corrigés : chaque test échouait (ou plantait) avant la correction correspondante."""
import json
import math
from types import SimpleNamespace

import numpy as np
import pytest

from simforge import ow_protocol as P
from simforge import ped_protocol as PP


def _tm(t, vbus, pos=0.0):
    return P.Telemetry(t=t, pos=pos, pos_raw=0, vel=0, iq=0, torque=0, vbus=vbus, ibus=0, ibrake=0, fet_c=None,
                       motor_c=None, state=1, axis_err=0, motor_err=0, enc_err=0, ctrl_err=0, buttons=0)


# ---------------------------------------------------------------- Moniteur / Codeur
def test_courbe_reduite_garde_les_pics():
    """Un pic et un creux de 1 ms dans 10 s à 1 kHz : l'ancien « 1 point sur 4 » les effaçait."""
    from simforge.tab_monitor import Ring
    r = Ring()
    for i in range(12000):
        r.push(_tm(i / 1000, 24.0 + (6.0 if i == 11017 else 0.0) - (5.0 if i == 10503 else 0.0)))
    d = r.last(10.0, bins=1000)
    assert len(d["vbus"]) <= 2000
    assert d["vbus"].max() == 30.0 and d["vbus"].min() == 19.0
    assert np.all(np.diff(d["t"]) >= 0)
    assert d["t"][-1] == pytest.approx(11.999)


def test_courbe_courte_non_reduite():
    from simforge.tab_monitor import Ring
    r = Ring()
    for i in range(50):
        r.push(_tm(i / 1000, float(i)))
    d = r.last(10.0)
    assert list(d["vbus"]) == [float(i) for i in range(50)]


# ---------------------------------------------------------------- pédales
class _Dev:
    """Port de pédale : envoie un état, puis l'écriture échoue (câble débranché pendant un envoi)."""

    def __init__(self):
        st = {n: (0 if c == 1 else [0] * c) for n, _t, c in PP.STATE_BASIC_FIELDS}
        st["pedalFirmwareVersion_au8"] = [26, 43, 7]
        self.out = PP.frame(PP.T_STATE, PP._pack(PP.STATE_BASIC_FIELDS, PP.STATE_S, st), tag=1)
        self.closed = False

    def read(self):
        b, self.out = self.out, b""
        return b

    def write(self, b):
        raise OSError("port retiré")

    def close(self):
        self.closed = True


def test_pedale_ecriture_impossible_signalee(qapp):
    from simforge.ped_device import PedalManager, PedalLink
    mgr = PedalManager()
    logs = []
    mgr.log.connect(lambda lvl, msg: logs.append((lvl, msg)))
    dev = _Dev()
    link = PedalLink(mgr, "COM8", lambda: dev)
    link.run()                          # dans ce thread : se termine dès l'échec d'écriture au lieu de planter
    assert dev.closed
    assert any(lvl == "warn" and "COM8" in msg for lvl, msg in logs)


def test_pedale_simulee_role_verrouille_sauf_enregistrement():
    """Comme le firmware : « Appliquer » ne change pas le rôle d'une pédale assignée, « Enregistrer » oui."""
    from simforge.ped_device import FakePedalPort
    fake = FakePedalPort(2)
    c = dict(fake.cfg, pedalType_u8=1)
    fake.write(PP.build_config(c, store=False, tag=2))
    assert (fake.tag, fake.cfg["pedalType_u8"]) == (2, 2)
    fake.write(PP.build_config(c, store=True, tag=2))
    assert (fake.tag, fake.cfg["pedalType_u8"]) == (1, 1)


def test_cinematique_coherente():
    """Les points calculés respectent les cotes : |OC| = b et |BC| = a, à toutes les positions de course."""
    from simforge.tab_pedals import KinematicsView
    c = PP.default_config()
    k = SimpleNamespace(cfg=c)
    for sled in (0.0, 30.0, 85.0):
        th = KinematicsView._angle(k, sled)
        b, a = c["lengthPedalB_i16"], c["lengthPedalA_i16"]
        C = (b * math.cos(th), b * math.sin(th))
        B = (c["lengthPedalCHorizontal_i16"] + sled, c["lengthPedalCVertical_i16"])
        assert math.dist(C, B) == pytest.approx(a, abs=1e-6)
    # la pédale se couche quand le chariot avance
    assert KinematicsView._angle(k, 85.0) < KinematicsView._angle(k, 0.0)


# ---------------------------------------------------------------- fichiers et préférences
def test_export_json_atomique(tmp_path, qapp, monkeypatch):
    from simforge import widgets
    warned = []
    monkeypatch.setattr(widgets.QMessageBox, "warning", lambda *a, **k: warned.append(a))
    f = tmp_path / "profil.json"
    f.write_text('{"ancien": 1}', encoding="utf-8")
    assert widgets.save_json(None, str(f), {"nouveau": 2})
    assert json.loads(f.read_text(encoding="utf-8")) == {"nouveau": 2}
    assert not (tmp_path / "profil.json.tmp").exists()
    # échec en cours d'écriture : l'ancien fichier reste intact, pas de .tmp oublié, message affiché
    assert widgets.save_json(None, str(f), {"x": object()}) is False
    assert json.loads(f.read_text(encoding="utf-8")) == {"nouveau": 2}
    assert not (tmp_path / "profil.json.tmp").exists() and len(warned) == 1
    assert widgets.save_json(None, str(tmp_path / "dossier_absent" / "p.json"), {"x": 1}) is False
    assert len(warned) == 2


def test_preferences_overlay_abimees():
    from simforge.tab_overlay import _valid
    assert _valid("pos", [10, 20]) and _valid("pos", None)
    assert not _valid("pos", "10,20") and not _valid("opacity", "85") and not _valid("show", 3)
    assert _valid("opacity", 70) and _valid("show", ["angle"])


# ---------------------------------------------------------------- interface
def test_molette_ne_prend_plus_le_focus(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDoubleSpinBox, QComboBox
    from simforge.widgets import install_wheel_guard
    install_wheel_guard(qapp)
    for w in (QDoubleSpinBox(), QComboBox()):
        w.ensurePolished()
        assert w.focusPolicy() & Qt.WheelFocus != Qt.WheelFocus


def test_force_test_suit_l_etat_reel_du_retour_de_force():
    """Le Joy tester ferme le retour de force partagé : Force test ne doit plus le croire ouvert."""
    from simforge.tab_force import ForceTab
    sdl = SimpleNamespace(haptic=object())
    tab = SimpleNamespace(sdl=sdl)
    assert ForceTab.haptic_ok.fget(tab)
    sdl.haptic = None
    assert not ForceTab.haptic_ok.fget(tab)


def test_import_profil_volant_lecture_seule_ignoree(qapp):
    """Les valeurs en lecture seule exportées par SimForge ne sont plus comptées « non gérées » à l'import."""
    from simforge.ow_device import Board
    from simforge.tab_params import SettingsTab
    tab = SettingsTab(Board(demo=True))
    ro = next(f.path for f in P.FIELDS if f.ro)
    tab.apply_profile({ro: "0.1", "chemin.inconnu": "1"}, "profil.json")
    txt = tab.import_lbl.text()
    assert ": 1" in txt.splitlines()[-1]        # seul « chemin.inconnu » est non géré


def test_alarmes_servo_bit_ponctuel(qapp):
    """Le bit « effacer les alarmes » ne part qu'avec la commande dédiée, jamais avec un réglage ou un enregistrement."""
    from simforge.ped_device import PedalManager
    mgr = PedalManager()
    sent = []
    mgr.links["COM8"] = SimpleNamespace(send=lambda b, what: sent.append(b), info=SimpleNamespace(tag=1))
    c = PP.default_config()
    c["debugFlags0_u8"] = PP.DBG_CLEAR_ALARMS | PP.DBG_EXT_STATE      # relu d'une pédale qui l'a gardé
    assert mgr.send_config("COM8", c, True) == ""
    assert mgr.send_config("COM8", c, False, clear_alarms=True) == ""
    flags = [PP.Parser().feed(b)[0].data["debugFlags0_u8"] for b in sent]
    assert flags == [PP.DBG_EXT_STATE, PP.DBG_EXT_STATE | PP.DBG_CLEAR_ALARMS]


def test_alarmes_servo_expliquees():
    from simforge.ped_device import FakePedalPort
    fake = FakePedalPort(2)
    fake.write(PP.build_config(dict(fake.cfg, debugFlags0_u8=PP.DBG_CLEAR_ALARMS), store=False, tag=2))
    p = PP.Parser()
    p.feed(fake.read())
    hist = [ln for ln in p.lines if "alarm history:" in ln]
    assert hist and PP.servo_hint(hist[0]) == dict(PP.SERVO_MSG_HINTS)["Overvoltage"]
    assert fake.cfg["debugFlags0_u8"] & PP.DBG_CLEAR_ALARMS == 0          # remis à 0, comme le firmware
    assert PP.servo_hint("Servo communication lost!") and PP.servo_hint("Setup end") is None


# ---------------------------------------------------------------- volant : activation du moteur
class _Link:
    def __init__(self, ready="1", reaches=True):
        self.ready, self.reaches, self.cmds, self.state = ready, reaches, [], "1"

    def r(self, path, timeout=0.5):
        return {"axis0.encoder.is_ready": self.ready, "axis0.current_state": self.state,
                "axis0.error": "0"}.get(path)

    def w(self, path, value, timeout=0.5):
        self.cmds.append((path, value))
        if self.reaches:
            self.state = value
        return True, value

    def system(self, cmd):
        self.cmds.append(("system", cmd))


def _worker(link, tm):
    from simforge.ow_device import SerialThread
    got = []
    sig = SimpleNamespace(emit=lambda *a: got.append(a))
    b = SimpleNamespace(last=tm, half_range=450.0, log=sig, arm_refused=sig, rearm_needs_cal=sig)
    return SimpleNamespace(b=b, link=link), got, SerialThread._closed_loop


def test_activation_refusee_hors_course():
    """Volant tourné au-delà de sa course moteur coupé : l'activation faisait un à-coup puis une erreur."""
    link = _Link()
    tm = _tm(1.0, 24.0)
    tm.pos_raw = 32767                                  # rapport HID saturé : volant hors de la course
    w, got, closed_loop = _worker(link, tm)
    closed_loop(w)
    assert not any(p == "axis0.requested_state" for p, _v in link.cmds)
    assert got


def test_activation_efface_toujours_les_erreurs():
    """Au démarrage, sans télémétrie, une erreur de la carte bloquait « Activer le moteur » sans message."""
    link = _Link()
    w, got, closed_loop = _worker(link, None)
    closed_loop(w)
    assert link.cmds[0] == ("system", "sc") and ("axis0.requested_state", "8") in link.cmds
    link = _Link(reaches=False)                         # la carte reste au repos : l'utilisateur est prévenu
    w, got, closed_loop = _worker(link, None)
    closed_loop(w)
    assert any("erreur" in str(a).lower() or "error" in str(a).lower() for a in got)


# ---------------------------------------------------------------- pédale « un câble » (USB natif)
def test_port_natif_dtr_leve(monkeypatch):
    """Firmware « un câble » : rien n'est envoyé sans DTR et RTS levés ; la puce série, elle, les garde bas."""
    from simforge import ped_device
    opened = []

    class _Serial:
        def open(self):
            opened.append((self.port, self.baudrate, self.dtr, self.rts))

    monkeypatch.setattr(ped_device.serial, "Serial", _Serial)
    ped_device.SerialPort("COM9", 921600, native=True)
    ped_device.SerialPort("COM8", PP.BAUD)
    assert opened == [("COM9", 921600, True, True), ("COM8", PP.BAUD, False, False)]


def test_version_firmware_simforge():
    assert PP.fw_text((26, 43, 7)) == "26.43.07" and not PP.simforge_fw((26, 43, 7))
    assert PP.fw_text((26, 43, 107)) == "26.43.07 SimForge" and PP.simforge_fw((26, 43, 107))
    assert PP.fw_text(None) == "?" and not PP.simforge_fw(None)


def test_import_profil_pedale_complet(qapp, tmp_path, monkeypatch):
    """L'import ne reprenait que les réglages affichés : effets, fenêtres, axe frein d'orteil restaient ceux de la
    pédale (35 champs perdus)."""
    from simforge import tab_pedals
    from simforge.ped_device import PedalManager
    tab = tab_pedals.PedalsTab(PedalManager(demo=True))
    tab.port = "DEMO-FREIN"
    cfg = PP.default_config()
    tab._on_config("DEMO-FREIN", dict(cfg))
    prof = dict(cfg, cvAmp1_u8=cfg["cvAmp1_u8"] + 7, gWindow_u8=cfg["gWindow_u8"] + 3, maxForce_fl32=55.0)
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"config": prof}), encoding="utf-8")
    monkeypatch.setattr(tab_pedals.QFileDialog, "getOpenFileName", lambda *a, **k: (str(f), ""))
    tab.import_()
    eff = tab._effective()
    assert {k: eff[k] for k in ("cvAmp1_u8", "gWindow_u8", "maxForce_fl32")} == \
        {k: prof[k] for k in ("cvAmp1_u8", "gWindow_u8", "maxForce_fl32")}
    tab._on_config("DEMO-FREIN", dict(prof))            # relu après envoi : plus rien en attente
    assert tab._extra == {}


def test_identifier_vibre_vraiment(qapp):
    """Un seul déclenchement ABS ne dure que 100 ms dans le firmware, et l'amplitude ABS vaut 0 par défaut :
    « Identifier » ne faisait rien. Il impose un ABS sur la course, le relance toutes les 50 ms puis remet la
    configuration de la pédale."""
    import time as _t
    from simforge import tab_pedals
    from simforge.ped_device import PedalManager
    tab = tab_pedals.PedalsTab(PedalManager(demo=True))
    tab.port = "DEMO-FREIN"
    cfg = PP.default_config()
    cfg["absAmplitude_u8"] = 0
    tab._on_config("DEMO-FREIN", dict(cfg))
    sent, acts = [], []
    tab.m = SimpleNamespace(send_config=lambda p, c, store, **k: sent.append((dict(c), store, k)) or "",
                            action=lambda p, what="", **k: acts.append(k.get("triggerAbs_u8")))
    tab.identify()
    end = _t.monotonic() + 1.0
    while _t.monotonic() < end:
        qapp.processEvents()
        _t.sleep(0.01)
    assert sent[0][0]["absAmplitude_u8"] > 0 and sent[0][0]["absForceOrTarvelBit_u8"] == 1
    assert sent[0][2] == {"reread": False} and not sent[0][1]
    assert sent[-1][0] == cfg                           # configuration de la pédale remise
    assert acts.count(1) >= 8 and acts[-1] == 0         # relancé pendant ~0,6 s, puis arrêté


def test_flashage_reessaie_moins_vite(qapp, monkeypatch):
    """À 921600 bauds, certains câbles ou pilotes CH343 échouent : on réessaie à 115200 au lieu d'abandonner."""
    import sys as _sys
    from simforge.tab_pedal_fw import Flasher
    bauds = []

    def main(args):
        bauds.append(args[args.index("--baud") + 1])
        if bauds[-1] == "921600":
            raise RuntimeError("Serial data stream stopped")

    monkeypatch.setitem(_sys.modules, "esptool", SimpleNamespace(__version__="5.1", main=main))
    f = Flasher()
    res = []
    f.done.connect(lambda ok, msg: res.append(ok))
    f._run("COM8", {"chip": "esp32s3", "dir": ".", "parts": [["0x0", "x.bin"]]}, False)
    assert bauds == ["921600", "115200"] and res == [True]


def test_demarrage_avec_index_z(qapp, monkeypatch):
    """Codeur avec fil Z (côté moteur, réducteur) : recherche d'index puis calage, et démarrage qui ne refait plus
    le grand tour de calage (index cherché, calage gardé)."""
    import time as _t
    from simforge import tab_setup
    from simforge.ow_device import Board
    from simforge.tab_params import SettingsTab
    monkeypatch.setattr(tab_setup.QMessageBox, "question", lambda *a, **k: tab_setup.QMessageBox.Yes)
    monkeypatch.setattr(tab_setup.QMessageBox, "warning", lambda *a, **k: tab_setup.QMessageBox.Yes)
    b = Board(demo=True)
    st = SettingsTab(b)
    page = tab_setup.SetupTab(b, st)
    b.start()

    def wait(cond, s):
        end = _t.monotonic() + s
        while _t.monotonic() < end and not cond():
            qapp.processEvents()
            _t.sleep(0.02)
        return cond()

    assert wait(lambda: st.rows["axis0.encoder.config.use_index"].read_ok and page.last is not None, 8)
    b.fake.motor_cal = True
    b.fake.v["axis0.motor.config.phase_resistance"] = "0.27"
    st.rows["axis0.motor.config.phase_resistance"].device = 0.27
    page.index_startup()
    assert wait(lambda: "✔" in page.s7.res.text() or "✖" in page.s7.res.text(), 15), page.s7.res.text()
    assert "✔" in page.s7.res.text()
    assert b.fake.index_found and b.fake.enc_ready
    v = b.fake.v
    assert (v["axis0.encoder.config.use_index"], v["axis0.encoder.config.pre_calibrated"],
            v["axis0.config.startup_encoder_index_search"], v["axis0.config.startup_encoder_offset_calibration"]) \
        == ("1", "1", "1", "0")
    b.stop() if hasattr(b, "stop") else None


def test_signaux_abz(qapp):
    """Affichage A/B/Z : sens du comptage, impulsion Z vue, et tours de codeur par tour moteur (rapport non entier
    signalé, ex. courroie 72/16 : 4,5)."""
    from simforge.ow_device import Board
    from simforge.tab_params import SettingsTab
    from simforge.tab_encoder import EncoderTab
    b = Board(demo=True)
    tab = EncoderTab(b, SettingsTab(b))
    tab.vals["axis0.encoder.config.cpr"] = "45000"
    for cnt, zh in ((0, 0), (500, 0), (900, 1), (5000, 1), (10900, 2)):
        tab._abz({"axis0.encoder.shadow_count": str(cnt), "axis.zhits": str(zh)})
    assert "↑" in tab.s["ab"].v.text() and "(1)" in tab.s["z"].v.text()      # nouvelle impulsion vue
    assert tab.s["z_gap"].v.text() == "10000" and tab.s["z_ratio"].v.text() == "4.50"


# ---------------------------------------------------------------- appairage sans fil
def test_trame_appairage_aller_retour():
    macs = [bytes(6), bytes((1, 2, 3, 4, 5, 6)), None, bytes((9, 9, 9, 9, 9, 9))]
    (f,) = PP.Parser().feed(PP.build_mac(macs, 6, True))
    assert (f.ptype, f.version, f.store) == (PP.T_MAC, PP.MAC_VERSION, 1)
    assert f.data["macs"][1] == macs[1] and f.data["macs"][3] == macs[3] and f.data["channel"] == 6
    assert f.data["assigned"] == [0, 1, 0, 1]
    assert len(PP.build_mac()) == 6 + 38 + 4            # sizeof(DapMacAddresses_t)


def test_table_appairage_fusion():
    from simforge.tab_pedal_wireless import merge_table
    z, br, fr, ac, old = bytes(6), bytes([3] * 6), bytes([1] * 6), bytes([2] * 6), bytes([7] * 6)
    bridge = {"macs": [old, z, z, z], "own": br, "node": 3, "channel": 11}
    brake = {"macs": [z] * 4, "own": fr, "node": 1, "channel": 11}
    macs, err = merge_table({"COM8": brake}, bridge)
    assert not err and macs == [old, fr, z, br]          # embrayage déjà appairé conservé
    # la pédale a changé de rôle : son ancienne case est vidée
    macs, err = merge_table({"COM8": dict(brake, node=2)}, dict(bridge, macs=[z, fr, z, z]))
    assert macs == [z, z, fr, br]
    assert merge_table({"COM8": brake, "COM9": dict(brake, own=ac)}, bridge)[1]       # deux fois le même rôle
    assert merge_table({"COM8": brake}, None)[1]                                      # récepteur inconnu
    assert merge_table({"COM8": dict(brake, node=4)}, bridge)[1]                      # pédale sans rôle


def test_appairage_de_bout_en_bout_en_demo(qapp, monkeypatch):
    """Détecter puis Appairer : pédales et récepteur simulés reçoivent la même table, et une trame d'appairage
    (version 1) ne fait pas passer la pédale pour « firmware incompatible »."""
    import time as _t
    from simforge import tab_pedal_wireless as W
    from simforge.ped_device import PedalManager, FakeBridgePort
    monkeypatch.setattr(W.QMessageBox, "question", lambda *a, **k: W.QMessageBox.Yes)
    FakeBridgePort.table = ([bytes(6)] * 4, 11)
    mgr = PedalManager(demo=True)
    tab = W.WirelessTab(mgr)
    mgr.start()

    def wait(cond, s=6):
        end = _t.monotonic() + s
        while _t.monotonic() < end and not cond():
            qapp.processEvents()
            _t.sleep(0.02)
        return cond()

    assert wait(lambda: len(mgr.pedals()) == 2)
    tab.detect()
    assert wait(lambda: len(tab.ped) == 2 and tab.bridge is not None)
    tab.ch.setValue(6)
    tab.pair()
    assert wait(lambda: FakeBridgePort.table[1] == 6 and not tab.busy)
    macs = FakeBridgePort.table[0]
    assert macs[3] == FakeBridgePort.own_mac and any(macs[1]) and any(macs[2]) and not any(macs[0])
    assert wait(lambda: all(t["macs"] == macs and t["channel"] == 6 for t in tab.ped.values()))
    assert not any(p.incompatible for p in mgr.pedals())
    mgr.stop()


def test_recepteur_par_hid(monkeypatch):
    """Le récepteur répond à l'appairage par l'interface HID de sa prise USB (rapports 3 → et 2 ←, découpés en
    morceaux de 60 octets avec type, taille totale et taille du morceau)."""
    from simforge import ped_device as D
    own = bytes((0x34, 0x85, 0x18, 0xBB, 0, 3))
    sent = []

    class _Dev:
        def __init__(self):
            self.rx = []

        def open_path(self, path):
            assert path == b"vendeur"

        def write(self, pkt):
            assert len(pkt) == 64 and pkt[0] == D.HID_OUT and pkt[1] == D.HID_START
            total, n = pkt[2], pkt[3]
            sent.append(bytes(pkt[4:4 + n]))
            assert total == n == 48
            reply = PP.frame(PP.T_MAC, PP.MAC_S.pack(0, 0, 0, 0, bytes(24), own, 3, 11), 0, 0, PP.MAC_VERSION)
            # réponse en deux morceaux, précédée d'un autre rapport (manette) à ignorer
            self.rx = [[1] + [0] * 12, [D.HID_IN, 1, 48, 30] + list(reply[:30]) + [0] * 29,
                       [D.HID_IN, 2, 48, 18] + list(reply[30:]) + [0] * 41]

        def read(self, n, timeout):
            return self.rx.pop(0) if self.rx else []

        def close(self):
            pass

    fake_hid = SimpleNamespace(device=_Dev, enumerate=lambda v, p: [
        {"path": b"manette", "usage_page": 1}, {"path": b"vendeur", "usage_page": 0xFF00}])
    monkeypatch.setattr(D, "hid", fake_hid)
    mgr = D.PedalManager.__new__(D.PedalManager)
    mgr.demo, mgr.paused, mgr.probing, mgr.links = False, set(), {}, {}
    assert D.BRIDGE_USB in mgr.bridge_ports()
    got, err = mgr.bridge_exchange(D.BRIDGE_USB, PP.build_mac(), wait=1.0)
    assert not err and got["own"] == own and got["node"] == 3 and got["channel"] == 11
    assert PP.Parser().feed(sent[0])[0].ptype == PP.T_MAC
