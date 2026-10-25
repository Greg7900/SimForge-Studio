"""Protocole Odrive-Wheel : rapport HID et lecture/écriture des réglages."""
import math

from simforge import ow_protocol as P


def _tm(**kw):
    base = dict(t=1.0, pos=0.0, pos_raw=12345, vel=1.234, iq=-2.5, torque=0.75, vbus=39.57, ibus=-1.25, ibrake=0.5,
                fet_c=31.0, motor_c=None, state=P.CLOSED_LOOP, axis_err=0, motor_err=0x01000000, enc_err=0,
                ctrl_err=0xFFFFFFFF, buttons=5, axes=(1, 2, 3, 4))
    base.update(kw)
    return P.Telemetry(**base)


def test_rapport_hid_aller_retour():
    tm = _tm()
    back = P.parse_report(P.build_report(tm), 2.0, 450.0)
    assert back.pos_raw == tm.pos_raw and math.isclose(back.pos, 12345 / 32767 * 450.0)
    assert (back.vel, back.iq, back.torque, back.vbus, back.ibus) == (1.234, -2.5, 0.75, 39.57, -1.25)
    assert back.fet_c == 31.0 and back.motor_c is None
    assert back.motor_err == 0x01000000 and back.ctrl_err == 0xFFFFFFFF      # u32, pas de signe
    assert back.state == P.CLOSED_LOOP and back.any_error


def test_rapport_hid_court_ou_etranger():
    raw = P.build_report(_tm())
    short = P.parse_report(raw[:31], 0.0, 450.0)          # ancien firmware sans températures ni erreurs
    assert short is not None and short.fet_c is None and short.motor_err == 0
    assert P.parse_report(b"\x02" + raw[1:], 0.0, 450.0) is None
    assert P.parse_report(raw[:20], 0.0, 450.0) is None


def test_field_parse_cas_limites():
    f_int = P.Field("x", "x", "int")
    assert f_int.parse("12.0") == 12
    assert f_int.parse("inf") is None                      # OverflowError avant la correction
    assert f_int.parse("abc") is None and f_int.parse(None) is None
    f_bool = P.Field("x", "x", "bool")
    assert (f_bool.parse("True"), f_bool.parse("0"), f_bool.parse("2")) == (1, 0, None)
    assert P.Field("x", "x", "float").parse("inf") == math.inf


def test_field_fmt_sans_notation_exponentielle():
    f = P.Field("x", "x", "float")
    assert f.fmt(0.000012) == "0.000012"
    assert f.fmt(-0.0) == "0" and f.fmt(10.0) == "10"
    assert f.fmt(math.inf) == "inf"
    assert P.Field("x", "x", "bool").fmt(True) == "1"


def test_to_float():
    assert P.to_float("1.5") == 1.5
    assert P.to_float(None) is None and P.to_float("—") is None
