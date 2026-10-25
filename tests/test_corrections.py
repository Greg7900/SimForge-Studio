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
