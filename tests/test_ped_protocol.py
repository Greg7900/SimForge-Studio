"""Protocole série des pédales ChrGri : trames, découpage du flux, contrôles de plausibilité."""
from simforge import ped_protocol as PP


def test_fletcher16_valeur_connue():
    # valeurs de référence de l'algorithme de Fletcher-16
    assert PP.fletcher16(b"abcde") == 0xC8F0
    assert PP.fletcher16(b"abcdef") == 0x2057


def test_config_aller_retour():
    cfg = PP.default_config()
    cfg["maxForce_fl32"] = 72.5
    frames = PP.Parser().feed(PP.build_config(cfg, store=True, tag=2))
    assert len(frames) == 1
    f = frames[0]
    assert (f.ptype, f.store, f.tag, f.version) == (PP.T_CONFIG, 1, 2, PP.VERSION)
    assert f.data["maxForce_fl32"] == 72.5
    assert {k: f.data[k] for k in PP.CONFIG_NAMES if k != "maxForce_fl32"} == \
        {k: cfg[k] for k in PP.CONFIG_NAMES if k != "maxForce_fl32"}


def test_flux_coupe_et_texte_melange():
    """Trames coupées en morceaux, texte du firmware entre elles, octet corrompu : rien ne se perd ni ne plante."""
    act = PP.build_action(tag=1, systemAction_u8=PP.ACT_BEEP)
    bad = bytearray(act)
    bad[8] ^= 0x01                                      # charge utile corrompue : CRC faux
    # (pas ^ 0xFF : 0x00 et 0xFF sont indiscernables pour Fletcher-16, calculé modulo 255 — limite du firmware)
    stream = b"Setup end\r\n" + act[:5] + act[5:] + bytes(bad) + b"[ESPNOW TX] Unhealthy\r\n" + act
    p = PP.Parser()
    frames = []
    for i in range(0, len(stream), 7):                  # arrive par paquets de 7 octets
        frames += p.feed(stream[i:i + 7])
    assert [f.ptype for f in frames] == [PP.T_ACTION, PP.T_ACTION]
    assert all(f.data["systemAction_u8"] == PP.ACT_BEEP for f in frames)
    assert p.bad_crc >= 1
    # le message qui suit la trame abîmée n'est plus perdu (quelques restes imprimables peuvent le précéder)
    assert p.lines[0] == "Setup end" and len(p.lines) == 2
    assert p.lines[1].endswith("[ESPNOW TX] Unhealthy")


def test_autre_version_signalee_sans_decodage():
    raw = PP.frame(PP.T_ACTION, PP._pack(PP.ACTION_FIELDS, PP.ACTION_S, {n: 0 for n, _t, _c in PP.ACTION_FIELDS}),
                   version=PP.VERSION + 1)
    (f,) = PP.Parser().feed(raw)
    assert f.version == PP.VERSION + 1 and f.data == {}


def test_plausible_config_usine():
    assert PP.plausible(PP.default_config()) == []


def test_plausible_refuse_le_mode_palonnier():
    # le firmware lit « 2e point de la courbe = 1 % » comme un palonnier d'avion
    c = PP.default_config()
    c["relativeForce01_u8"] = 1
    assert PP.plausible(c)
    c["relativeForce01_u8"] = 2
    assert PP.plausible(c) == []


def test_plausible_comme_le_firmware():
    c = PP.default_config()
    c["pedalStartPosition_u8"], c["pedalEndPosition_u8"] = 50, 53     # moins de 5 % de course
    assert PP.plausible(c)
    c = PP.default_config()
    c["lengthPedalTravel_i16"] = 5
    assert PP.plausible(c)
    c = PP.default_config()
    c["preloadForce_fl32"] = c["maxForce_fl32"]                        # précharge ≥ force maxi
    assert PP.plausible(c)


def test_catalogue_des_reglages():
    names = [f.name for f in PP.PFIELDS]
    assert len(names) == len(set(names))
    for f in PP.PFIELDS:
        assert f.name in PP.CONFIG_NAMES
        assert f.group in PP.TABS_CURVE + PP.TABS_GENERAL + PP.TABS_FX
