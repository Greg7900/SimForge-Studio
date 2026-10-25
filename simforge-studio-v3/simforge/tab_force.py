"""Onglet Force test, sur le modèle de ForceTest : 1) source, 2) effet, 3) réglages + LANCER, avec visualisation.

Les effets passent par DirectInput, exactement comme ceux d'un jeu. Odrive-Wheel gère tous les effets DirectX
(ressort, constante, périodiques, frottement, amortissement, inertie, rampe), et la carte remonte le couple réel
en N·m : on voit tout de suite si elle applique ce qui est demandé.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
                               QComboBox, QCheckBox, QSpinBox, QStackedWidget, QButtonGroup, QFrame, QScrollArea)

from . import ow_protocol as P
from .i18n import T
from .theme import C
from .widgets import card, hint, SettingRow, ValueReadout, Led, WheelDial, CenterBar

PERIODIC = [(T("Sinus"), "sine"), ("Triangle", "triangle"), (T("Dent de scie ↑"), "sawup"),
            (T("Dent de scie ↓"), "sawdown")]

# clé, libellé, ce qu'on doit sentir, paramètres, gain du firmware qui s'applique
EFFECTS = [
    ("spring", T("Ressort (centrage)"),
     T("Le volant revient au centre, d'autant plus fort qu'on s'en éloigne. « Centre » décale le point de repos."),
     {"coeff": (T("Raideur"), 0, 100, 30, "%"), "center": (T("Centre"), -100, 100, 0, "%"),
      "saturation": (T("Saturation"), 0, 100, 100, "%"), "deadband": (T("Zone morte"), 0, 100, 0, "%")}, "fx.spring"),
    ("constant", T("Force constante"),
     T("Pousse en continu d'un côté : négatif = vers la gauche, positif = vers la droite. "
       "Vérifie que le sens correspond à celui du jeu."),
     {"level": (T("Niveau  (← gauche · droite →)"), -100, 100, 20, "%")}, None),
    ("periodic", T("Vibration (périodique)"),
     T("Vibration régulière. Période courte = vibration rapide (bruit de route), longue = balancement."),
     {"magnitude": (T("Amplitude"), 0, 100, 20, "%"), "period_ms": (T("Période"), 10, 2000, 100, "ms"),
      "offset": (T("Décalage"), -100, 100, 0, "%")}, None),
    ("friction", T("Frottement"),
     T("Résistance constante quand on tourne, quelle que soit la vitesse."),
     {"coeff": (T("Coefficient"), 0, 100, 30, "%")}, "fx.friction"),
    ("damper", T("Amortissement"),
     T("Résistance proportionnelle à la vitesse : lentement c'est léger, vite c'est dur."),
     {"coeff": (T("Coefficient"), 0, 100, 30, "%")}, "fx.damper"),
    ("inertia", T("Inertie"),
     T("Le volant paraît plus lourd au démarrage et à l'arrêt."),
     {"coeff": (T("Coefficient"), 0, 100, 30, "%")}, "fx.inertia"),
    ("ramp", T("Rampe"),
     T("La force passe progressivement de « Départ » à « Arrivée » pendant la durée, puis s'arrête."),
     {"start": (T("Départ"), -100, 100, -20, "%"), "end": (T("Arrivée"), -100, 100, 20, "%"),
      "length_ms": (T("Durée"), 100, 10000, 2000, "ms")}, None),
]


def _row(label, lo, hi, val, unit=""):
    r = SettingRow(label, lo, hi, unit)
    r.set_label_width(170)
    r.set_value(val)
    return r


def _big(btn: QPushButton, h=40):
    btn.setMinimumHeight(h)
    btn.setCheckable(True)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet("text-align: left; padding-left: 14px; font-size: 10.5pt;")
    return btn


class ForceTab(QWidget):
    def __init__(self, board, sdl, settings, parent=None):
        super().__init__(parent)
        self.b = board
        self.sdl = sdl
        self.settings = settings
        self.running = False
        self.playing = None             # kind DirectInput en cours
        self.haptic_ok = False
        self._diag = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # ------------------------------------------------ bandeau sécurité
        sec = QFrame()
        sec.setObjectName("card")
        sl = QHBoxLayout(sec)
        sl.setContentsMargins(14, 8, 14, 8)
        sl.setSpacing(18)
        self.limit = _row(T("Force max des essais"), 0, 100, 25, "%")
        self.limit.set_label_width(0)
        self.limit.setMinimumWidth(330)
        sl.addWidget(self.limit)
        self.guard = QCheckBox(T("Coupure si survitesse >"))
        self.guard.setChecked(True)
        self.guard.setToolTip(T("Pendant un essai, le moteur est mis au repos (STOP) si la vitesse mesurée par la carte "
                                "dépasse le seuil, ou si le volant sort de la course réglée."))
        self.guard_v = QSpinBox()
        self.guard_v.setRange(60, 5000)
        self.guard_v.setValue(600)
        self.guard_v.setSuffix(" °/s")
        sl.addWidget(self.guard)
        sl.addWidget(self.guard_v)
        sl.addStretch()
        self.r_state = ValueReadout(T("Moteur"), "", big=False)
        sl.addWidget(self.r_state)
        self.r_spd = ValueReadout(T("Vitesse"), "°/s", big=False)
        sl.addWidget(self.r_spd)
        root.addWidget(sec)

        main = QHBoxLayout()
        main.setSpacing(12)

        # ------------------------------------------------ 1. source + 2. effet
        col1 = QVBoxLayout()
        col1.setSpacing(12)
        c, l = card(T("1. Source"))
        l.addWidget(hint(T("DirectInput — le même chemin que les jeux.")))
        st = QHBoxLayout()
        self.led = Led(C["dim"], 10)
        self.h_status = QLabel(T("Fermé"))
        self.h_status.setObjectName("hint")
        self.h_status.setWordWrap(True)
        self.b_retry = QPushButton(T("Ouvrir"))
        st.addWidget(self.led)
        st.addWidget(self.h_status, 1)
        st.addWidget(self.b_retry)
        l.addLayout(st)
        self.gain = SettingRow(T("Gain DirectInput"), 0, 100, "%", slider=False)
        self.gain.set_value(100)
        self.gain.edited.connect(lambda v: self.sdl.set_gain(v))
        l.addWidget(self.gain)
        self.b_diag = QPushButton(T("Tester si la carte répond"))
        self.b_diag.setToolTip(T("Envoie une force constante à gauche puis à droite (limitée par la force max) et "
                                 "vérifie que le couple mesuré par la carte suit. Volant lâché, moteur actif."))
        self.b_diag.clicked.connect(self.run_diag)
        l.addWidget(self.b_diag)
        self.diag_lbl = hint("")
        l.addWidget(self.diag_lbl)
        col1.addWidget(c)

        c, l = card(T("2. Effet"))
        self.eff_group = QButtonGroup(self)
        self.eff_group.setExclusive(True)
        self.eff_btns = {}
        for i, (key, title, *_rest) in enumerate(EFFECTS):
            b = _big(QPushButton(title), 36)
            self.eff_group.addButton(b, i)
            self.eff_btns[key] = b
            l.addWidget(b)
        l.addStretch()
        self.eff_btns["spring"].setChecked(True)
        col1.addWidget(c, 1)
        col1w = QWidget()
        col1w.setLayout(col1)
        col1.setContentsMargins(0, 0, 6, 0)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(col1w)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setFixedWidth(370)
        main.addWidget(sc, 0)

        # ------------------------------------------------ 3. réglages + lancer
        c, l = card(T("3. Réglages"))
        self.title = QLabel("")
        self.title.setObjectName("midValue")
        l.addWidget(self.title)
        self.desc = hint("")
        l.addWidget(self.desc)
        self.gain_note = hint("")
        l.addWidget(self.gain_note)
        self.stack = QStackedWidget()
        self.params = {}
        self.shape = QComboBox()
        for n, _ in PERIODIC:
            self.shape.addItem(n)
        for key, title, desc, params, _g in EFFECTS:
            page = QWidget()
            pl = QVBoxLayout(page)
            pl.setContentsMargins(0, 6, 0, 0)
            if key == "periodic":
                sr = QHBoxLayout()
                lab = QLabel(T("Forme"))
                lab.setMinimumWidth(170)
                sr.addWidget(lab)
                sr.addWidget(self.shape, 1)
                pl.addLayout(sr)
                self.shape.currentIndexChanged.connect(lambda _i: self.apply())
            self.params[key] = {}
            for name, (label, lo, hi, val, unit) in params.items():
                r = _row(label, lo, hi, val, unit)
                r.edited.connect(lambda _v: self.apply())
                self.params[key][name] = r
                pl.addWidget(r)
            pl.addStretch()
            self.stack.addWidget(page)
        l.addWidget(self.stack, 1)
        self.b_play = QPushButton()
        self.b_play.setCheckable(True)
        self.b_play.setMinimumHeight(54)
        self.b_play.setCursor(Qt.PointingHandCursor)
        self.b_play.setObjectName("primary")
        l.addWidget(self.b_play)
        main.addWidget(c, 1)

        # ------------------------------------------------ visualisation
        c, l = card(T("Ce que fait le volant"))
        self.dial = WheelDial(size=230)
        l.addWidget(self.dial, 0, Qt.AlignCenter)
        g = QGridLayout()
        self.r_ang = ValueReadout(T("Angle"), "°", big=False)
        self.r_tq = ValueReadout(T("Couple mesuré"), "N·m", big=False)
        self.r_iq = ValueReadout(T("Courant moteur"), "A", big=False)
        self.r_pct = ValueReadout(T("Du couple maxi"), "%", big=False)
        g.addWidget(self.r_ang, 0, 0)
        g.addWidget(self.r_tq, 0, 1)
        g.addWidget(self.r_iq, 1, 0)
        g.addWidget(self.r_pct, 1, 1)
        l.addLayout(g)
        self.tbar = CenterBar(color=C["blue"])
        self.tbar.setMinimumHeight(22)
        l.addWidget(self.tbar)
        self.r_cmd = ValueReadout(T("Commande envoyée"), "", big=False)
        l.addWidget(self.r_cmd)
        l.addWidget(hint(T("Barre bleue = couple de sortie de la carte, en % du couple maximum du volant. Commence "
                           "volant lâché : un ressort doit ramener le volant au centre, jamais l'emmener tout seul.")))
        l.addStretch()
        main.addWidget(c, 1)
        root.addLayout(main, 1)

        # ------------------------------------------------ liaisons
        self.eff_group.idToggled.connect(lambda _i, on: on and self._effect_changed())
        self.b_play.toggled.connect(self._play_toggled)
        self.b_retry.clicked.connect(self.open_haptic)
        self.limit.edited.connect(lambda _v: self.apply())
        self.guard.toggled.connect(lambda _v: self._arm())
        self.guard_v.valueChanged.connect(lambda _v: self._arm())
        self.b.telemetry.connect(self.on_batch)
        self._effect_changed()
        self._play_text()

    # ------------------------------------------------------------ état
    def param(self, path):
        r = self.settings.rows.get(path)
        return r.device if (r and r.read_ok) else None

    def current(self):
        i = self.eff_group.checkedId()
        return EFFECTS[i if i >= 0 else 0]

    def _arm(self):
        self.b.arm_guard(self.guard.isChecked() and (self.running or self._diag is not None), self.guard_v.value())

    def _play_text(self):
        self.b_play.setText(T("■  ARRÊTER L'EFFET") if self.running else T("▶  LANCER L'EFFET"))
        base = "font-size: 13pt; letter-spacing: 1px;"
        self.b_play.setStyleSheet(base + (f" background: {C['bad']}; color: white; border: none;"
                                          if self.running else ""))

    def _effect_changed(self):
        key, title, desc, _p, gpath = self.current()
        self.title.setText(title)
        self.desc.setText(desc)
        self.stack.setCurrentIndex([e[0] for e in EFFECTS].index(key))
        self._gain_note()
        if self.running:
            self._stop_outputs()
            self.apply()

    def _gain_note(self):
        gpath = self.current()[4]
        parts = []
        if gpath:
            g = self.param(gpath)
            if g is not None:
                parts.append(T("Gain de cet effet dans la carte : {g}/255 ({p} %).").format(g=int(g), p=f"{g / 2.55:.0f}"))
                if g == 0:
                    parts.append(T("Gain à 0 : l'effet ne fera rien (Réglages › Effets du jeu)."))
        mt = self.param("axis.maxtorque")
        if mt is not None:
            parts.append(T("100 % = {m} N·m (couple maximum du volant).").format(m=f"{mt:g}"))
        self.gain_note.setText(" ".join(parts))

    def _play_toggled(self, on):
        if on and self.b.estop:
            self.b_play.blockSignals(True)
            self.b_play.setChecked(False)
            self.b_play.blockSignals(False)
            self.h_status.setText(T("STOP enclenché : réarme-le en haut avant de lancer un effet."))
            return
        if on and not self.haptic_ok:
            self.open_haptic()
            if not self.haptic_ok:
                self.b_play.blockSignals(True)
                self.b_play.setChecked(False)
                self.b_play.blockSignals(False)
                return
        if on and self.b.state not in (None, P.CLOSED_LOOP):
            self.h_status.setText(T("Le moteur n'est pas actif (état : {s}) : l'effet ne fera rien tant qu'il n'est pas "
                                    "en boucle fermée.").format(s=P.state_text(self.b.state)))
        self.running = on
        if on:
            self.apply()
        else:
            self._stop_outputs()
        self._play_text()
        self._arm()

    # ------------------------------------------------------------ sorties
    def _scale(self, v):
        return v * self.limit.value() / 100.0

    def apply(self):
        if not self.running:
            return
        key = self.current()[0]
        p = {k: r.value() for k, r in self.params[key].items()}
        kind = PERIODIC[self.shape.currentIndex()][1] if key == "periodic" else key
        if self.playing and self.playing != kind:
            self.sdl.stop(self.playing)
            self.playing = None
        for name in ("level", "coeff", "magnitude", "offset", "start", "end"):
            if name in p:
                p[name] = self._scale(p[name])
        err = self.sdl.play(kind, p)
        if err:
            self.h_status.setText(T("Erreur {k} : {e}").format(k=kind, e=err))
            self.led.set(C["bad"])
        else:
            self.playing = kind
            main = next((p[n] for n in ("level", "coeff", "magnitude") if n in p), None)
            self.r_cmd.set(f"{kind} {main:+.0f} %" if main is not None else kind)
        self._arm()

    def _stop_outputs(self):
        self.sdl.stop_all()
        self.playing = None
        if hasattr(self, "r_cmd"):
            self.r_cmd.set("—")

    def stop_all(self):
        self.running = False
        self._diag = None
        self.b_play.blockSignals(True)
        self.b_play.setChecked(False)
        self.b_play.blockSignals(False)
        self._stop_outputs()
        self._play_text()
        self.b_diag.setEnabled(True)
        self.b.arm_guard(False)

    def open_haptic(self):
        err = self.sdl.open_haptic("ODrive-Wheel")
        if err:
            self.haptic_ok = False
            self.led.set(C["bad"])
            self.h_status.setText(err)
            return
        self.haptic_ok = True
        sup = self.sdl.supported()
        self.led.set(C["ok"])
        self.h_status.setText(T("Retour de force ouvert"))
        per = any(sup.get(k) for k in ("sine", "triangle", "sawup", "sawdown"))
        missing = []
        for key, title, _d, _p, _g in EFFECTS:
            ok = per if key == "periodic" else sup.get(key, False)
            self.eff_btns[key].setEnabled(ok)
            if not ok:
                missing.append(title)
        if missing:
            self.h_status.setText(T("Retour de force ouvert. Non annoncés par le pilote : {l}").format(
                l=", ".join(missing)))
        self.sdl.set_gain(self.gain.value())

    # ------------------------------------------------------------ diagnostic
    def run_diag(self):
        if self.b.estop or not self.b.hid_ok:
            self.diag_lbl.setText(T("Carte non connectée ou STOP enclenché."))
            return
        if self.b.state != P.CLOSED_LOOP:
            self.diag_lbl.setText(T("Le moteur doit être actif (boucle fermée) : bouton « Activer le moteur » en "
                                    "haut, ou onglet Mise en route."))
            return
        self.stop_all()
        if not self.haptic_ok:
            self.open_haptic()
            if not self.haptic_ok:
                self.diag_lbl.setText(T("DirectInput indisponible : {e}").format(e=self.h_status.text()))
                return
        lvl = min(30.0, float(self.limit.value()))
        self._diag = {"phase": 0, "lvl": lvl, "base": [], "pos": [], "neg": []}
        self.b_diag.setEnabled(False)
        self.diag_lbl.setText(T("Test en cours… volant lâché."))
        self.diag_lbl.setStyleSheet("")
        self._arm()
        steps = [(0, 400), (1, 700), (2, 700), (3, 0)]

        def step(i=0):
            if self._diag is None:
                return
            ph, dur = steps[i]
            self._diag["phase"] = ph
            if ph == 1:
                self.sdl.play("constant", {"level": -lvl})
            elif ph == 2:
                self.sdl.play("constant", {"level": +lvl})
            elif ph == 3:
                self.sdl.stop_all()
                self._diag_report()
                return
            QTimer.singleShot(dur, lambda: step(i + 1))
        step()

    def _diag_report(self):
        d = self._diag
        self._diag = None
        self.b_diag.setEnabled(True)
        self._arm()
        if d is None:
            return
        avg = lambda xs: sum(xs[len(xs) // 3:]) / max(1, len(xs[len(xs) // 3:]))
        b, n, p = avg(d["base"]), avg(d["neg"]), avg(d["pos"])
        if self.b.estop:
            self.diag_lbl.setText(T("Test interrompu par la sécurité."))
            return
        mt = self.param("axis.maxtorque") or 0
        expect = mt * d["lvl"] / 100 if mt else None
        resp = (p - b) - (n - b)
        if abs(resp) >= max(0.05, (expect or 0.25) * 0.3):
            sign = T("même sens") if resp > 0 else T("sens inversé")
            msg = T("✔ La carte applique la force : {n} / {p} N·m pour ∓{l} % demandés ({s}).").format(
                n=f"{n:+.2f}", p=f"{p:+.2f}", l=f"{d['lvl']:.0f}", s=sign)
            if expect:
                msg += " " + T("Attendu environ ±{e} N·m (hors gains des effets et filtres).").format(e=f"{expect:.2f}")
            self.diag_lbl.setText(msg)
            self.diag_lbl.setStyleSheet(f"color: {C['ok']};")
        else:
            self.diag_lbl.setText(T("✖ Aucune réaction du couple (repos {b}, gauche {n}, droite {p} N·m). Vérifie : "
                                    "moteur actif, force globale, couple maximum, gain DirectInput.")
                                  .format(b=f"{b:+.2f}", n=f"{n:+.2f}", p=f"{p:+.2f}"))
            self.diag_lbl.setStyleSheet(f"color: {C['warn']};")

    # ------------------------------------------------------------ affichage
    def on_batch(self, batch):
        tm = batch[-1]
        d = self._diag
        if d:
            key = {0: "base", 1: "neg", 2: "pos"}.get(d["phase"])
            if key:
                d[key].extend(s.torque for s in batch)
        if not self.isVisible():
            return
        mt = self.param("axis.maxtorque")
        pct = tm.torque / mt * 100 if mt else 0.0
        rng = self.param("axis.range") or self.b.half_range * 2
        self.dial.set(tm.pos, rng, pct)
        self.r_ang.set(f"{tm.pos:+.1f}")
        self.r_tq.set(f"{tm.torque:+.2f}", C["bad"] if abs(pct) >= 98 else None)
        self.r_iq.set(f"{tm.iq:+.2f}")
        self.r_pct.set(f"{pct:+.0f}" if mt else "—")
        spd = tm.vel * 360
        self.r_spd.set(f"{spd:+.0f}", C["bad"] if abs(spd) > self.guard_v.value() else None)
        act = tm.state == P.CLOSED_LOOP
        self.r_state.set(T("actif") if act else T("au repos") if tm.state == P.IDLE
                         else P.STATES.get(tm.state, ("?",))[0].lower(), C["ok"] if act else C["warn"])
        self.tbar.set(pct)

    def showEvent(self, e):
        self._gain_note()
        super().showEvent(e)
