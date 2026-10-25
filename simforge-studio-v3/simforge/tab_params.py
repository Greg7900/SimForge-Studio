"""Onglet Réglages : tous les paramètres du firmware Odrive-Wheel, lus dans la carte, modifiables et vérifiés.

Deux mémoires dans la carte :
  • réglages volant / effets (axis.*, fx.*, gpio.*, sys.vbusdiv) → « sys.save! », sans redémarrage ;
  • réglages ODrive (moteur, codeur, alimentation…)              → « ss », moteur au repos, la carte redémarre.
Rien n'est écrit sans être relu : la valeur affichée est toujours celle que la carte a retenue.
"""
from __future__ import annotations

import json
import math
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QCheckBox,
                               QComboBox, QDoubleSpinBox, QSlider, QScrollArea, QFileDialog,
                               QMessageBox)

from . import i18n
from . import ow_protocol as P
from .i18n import T
from .theme import C
from .widgets import card, hint, repolish, StatRow, TabPages, save_json


# ======================================================================
#  Ligne de réglage
# ======================================================================
class ParamRow(QWidget):
    edited = Signal(str, object)           # chemin, valeur brute (unités carte)

    def __init__(self, f: P.Field, label: str | None = None, label_width=250, parent=None):
        super().__init__(parent)
        self.f = f
        self.device = None                 # valeur retenue par la carte (unités carte), None = non lue
        self.read_ok = False
        self.state = "normal"
        self._block = False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        lay.setSpacing(10)
        self.lbl = QLabel(label if label is not None else f.label)
        self.lbl.setWordWrap(False)
        self.lbl.setMinimumWidth(max(label_width, self.lbl.sizeHint().width()) if label_width else 0)
        if f.tip:
            self.setToolTip(f.tip + "\n\n" + f.path)
        else:
            self.setToolTip(f.path)
        lay.addWidget(self.lbl)
        self.slider = None
        self.ed = None
        if f.ro:
            lay.addStretch(1)
            self.ed = QLabel("—")
            self.ed.setObjectName("midValue")
            self.ed.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lay.addWidget(self.ed)
            if f.unit:
                u = QLabel(f.unit)
                u.setObjectName("unit")
                lay.addWidget(u)
        elif f.kind == "bool":
            self.ed = QCheckBox()
            lay.addStretch(1)
            lay.addWidget(self.ed)
            self.ed.toggled.connect(lambda _v: self._user())
        elif f.kind == "enum":
            self.ed = QComboBox()
            for v, txt in f.items:
                self.ed.addItem(txt, v)
            lay.addStretch(1)
            lay.addWidget(self.ed)
            self.ed.currentIndexChanged.connect(lambda _i: self._user())
        else:
            if f.slider:
                self.slider = QSlider(Qt.Horizontal)
                self.slider.setRange(0, 1000)
                self.slider.setMinimumWidth(130)
                lay.addWidget(self.slider, 1)
                self.slider.valueChanged.connect(self._from_slider)
                self.slider.sliderReleased.connect(self._user)
            else:
                lay.addStretch(1)
            self.ed = QDoubleSpinBox()
            dec = f.dec if (f.kind == "float" or f.scale != 1) else 0
            self.ed.setDecimals(dec)
            self.ed.setRange(f.lo, f.hi)
            self.ed.setSingleStep(10 ** (-dec) if dec else 1)
            self.ed.setKeyboardTracking(False)
            self.ed.setAlignment(Qt.AlignRight)
            self.ed.setMinimumWidth(110)
            if f.unit:
                self.ed.setSuffix(" " + f.unit)
            lay.addWidget(self.ed)
            self.ed.valueChanged.connect(self._from_spin)
        self.dot = QLabel("●")
        self.dot.setFixedWidth(14)
        lay.addWidget(self.dot)
        self._set_enabled(False)
        self._style("normal")

    # ---------------------------------------------------------------- valeurs
    def _disp_to_slider(self, d):
        lo, hi = self.ed.minimum(), self.ed.maximum()
        return int(round((d - lo) / (hi - lo) * 1000)) if hi > lo else 0

    def _from_slider(self, s):
        if self._block:
            return
        lo, hi = self.ed.minimum(), self.ed.maximum()
        d = lo + (hi - lo) * s / 1000.0
        self._block = True
        self.ed.setValue(d)
        self._block = False
        self._mark()
        if not self.slider.isSliderDown():
            self._user()

    def _from_spin(self, d):
        if self._block:
            return
        if self.slider:
            self._block = True
            self.slider.setValue(self._disp_to_slider(d))
            self._block = False
        self._user()

    def value(self):
        """Valeur de l'éditeur, en unités carte."""
        f = self.f
        if f.ro:
            return self.device
        if f.kind == "bool":
            return 1 if self.ed.isChecked() else 0
        if f.kind == "enum":
            d = self.ed.currentData()
            return int(d) if d is not None else None
        return f.from_display(self.ed.value())

    def set_value(self, raw):
        """Affiche une valeur (unités carte) sans émettre de modification."""
        f = self.f
        self._block = True
        try:
            if f.ro:
                self.ed.setText(self._fmt_ro(raw))
            elif raw is None:
                pass
            elif f.kind == "bool":
                self.ed.setChecked(bool(raw))
            elif f.kind == "enum":
                i = self.ed.findData(int(raw))
                if i < 0:   # valeur que la liste ne connaît pas : on l'affiche au lieu de la remplacer
                    self.ed.addItem(T("Valeur inconnue ({v})").format(v=int(raw)), int(raw))
                    i = self.ed.count() - 1
                self.ed.setCurrentIndex(i)
            else:
                d = f.to_display(raw)
                if not math.isfinite(d):
                    d = self.ed.maximum() if d > 0 else self.ed.minimum()
                    self.lbl.setToolTip(T("La carte contient {v} : affiché à la borne.").format(v=raw))
                elif d < self.ed.minimum() or d > self.ed.maximum():
                    # ne jamais tronquer une valeur lue : on élargit la plage
                    lo, hi = min(d, self.ed.minimum()), max(d, self.ed.maximum())
                    self.ed.setRange(lo, hi)
                    self.lbl.setText(self.lbl.text().rstrip(" ⚑") + " ⚑")
                    self.lbl.setToolTip(T("Valeur de la carte ({v}) hors de la plage habituelle : affichée telle "
                                          "quelle.").format(v=f"{d:g}"))
                self.ed.setValue(d)
                if self.slider:
                    self.slider.setValue(self._disp_to_slider(d))
        finally:
            self._block = False
        self._mark()

    def _fmt_ro(self, raw):
        if raw is None:
            return "—"
        f = self.f
        if f.kind in ("int", "enum", "bool"):
            return str(int(raw))
        d = f.to_display(raw)
        return f"{d:.{f.dec}f}" if math.isfinite(d) else str(d)

    def set_device(self, text):
        """Texte lu dans la carte (None = non lu / absent de ce firmware)."""
        v = self.f.parse(text) if text is not None else None
        if v is None:
            self.read_ok = False
            self.device = None
            self._set_enabled(False)
            self.dot.setToolTip(T("Non lu : absent de ce firmware ou réponse illisible ({t}).").format(t=text))
            if self.f.ro:
                self.ed.setText("—")
            self._style("missing")
            return
        self.read_ok = True
        self.device = v
        self._set_enabled(True)
        self.set_value(v)
        self._style("normal")

    def modified(self) -> bool:
        if not self.read_ok or self.f.ro:
            return False
        v = self.value()
        return v is not None and not self.f.same(v, self.device)

    def _user(self):
        if self._block:
            return
        self._mark()
        self.edited.emit(self.f.path, self.value())

    def _mark(self):
        if self.state in ("pending",):
            return
        self._style("modified" if self.modified() else "normal")

    def _set_enabled(self, on):
        if self.ed is not None and not self.f.ro:
            self.ed.setEnabled(on)
        if self.slider:
            self.slider.setEnabled(on)

    def _style(self, st):
        self.state = st
        col = {"normal": C["line"], "modified": C["accent"], "pending": C["blue"], "error": C["bad"],
               "missing": C["panel2"], "saved_needed": C["warn"]}.get(st, C["line"])
        self.dot.setStyleSheet(f"color: {col};")
        tips = {"normal": T("Valeur lue dans la carte."), "modified": T("Modifié, pas encore envoyé."),
                "pending": T("Envoyé, en attente de relecture."),
                "saved_needed": T("Appliqué dans la carte, pas encore mémorisé (« Enregistrer »).")}
        if st in tips:
            self.dot.setToolTip(tips[st])
        if self.ed is not None and not self.f.ro:
            m = "true" if st == "modified" else "false"
            if self.ed.property("modified") != m:
                self.ed.setProperty("modified", m)
                repolish(self.ed)

    def error(self, msg):
        self._style("error")
        self.dot.setToolTip(T("Refusé par la carte : {m}").format(m=msg))


# ======================================================================
#  Contrôles de cohérence (sécurité)
# ======================================================================
def safety_checks(v: dict, vbus: float | None) -> list[tuple[str, str]]:
    """v : {chemin: valeur brute}. Retourne [(niveau 'bad'|'warn', texte)]."""
    out = []
    g = v.get
    mode, use_idx, enc_pre = g("axis0.encoder.config.mode"), g("axis0.encoder.config.use_index"), \
        g("axis0.encoder.config.pre_calibrated")
    if mode == 0 and use_idx == 0 and enc_pre == 1:
        out.append(("bad", T("Codeur incrémental sans index marqué « calage conservé » : au prochain allumage la carte "
                             "réutiliserait un calage faux (risque d'emballement). Décoche-le.")))
    if mode == 0 and use_idx == 0 and g("axis0.config.startup_closed_loop_control") == 1 \
            and g("axis0.config.startup_encoder_offset_calibration") == 0:
        out.append(("warn", T("Boucle fermée au démarrage sans calage du codeur : la carte s'arrêtera en erreur "
                              "UNKNOWN_PHASE_ESTIMATE à chaque allumage. Active « Caler le codeur ».")))
    if g("axis0.config.startup_encoder_offset_calibration") == 1 and g("axis0.motor.config.pre_calibrated") == 0 \
            and g("axis0.config.startup_motor_calibration") == 0:
        out.append(("warn", T("Calage du codeur au démarrage sans moteur calibré : il échouera. Marque le moteur "
                              "comme calibré après sa calibration.")))
    if g("axis0.controller.config.control_mode") not in (None, 1):
        out.append(("bad", T("Le mode de commande n'est pas « Couple » : le volant ne fonctionnera pas normalement.")))
    if g("axis0.controller.config.enable_overspeed_error") == 0:
        out.append(("warn", T("Coupure de survitesse désactivée : plus de protection en cas d'emballement.")))
    vl = g("axis0.controller.config.vel_limit")
    if vl is not None and vl > 20:
        out.append(("warn", T("Vitesse maxi {v} tr/s : très au-dessus d'un volant (2–8 tr/s). La protection "
                              "anti-emballement réagira tard.").format(v=f"{vl:g}")))
    ov, uv = g("config.dc_bus_overvoltage_trip_level"), g("config.dc_bus_undervoltage_trip_level")
    if vbus and vbus > 3:
        if ov is not None and ov <= vbus + 1.0:
            out.append(("bad", T("Coupure tension haute ({o} V) trop proche de la tension actuelle ({v} V) : "
                                 "la carte va couper au moindre freinage.").format(o=f"{ov:g}", v=f"{vbus:.1f}")))
        if uv is not None and uv >= vbus - 0.5:
            out.append(("bad", T("Coupure tension basse ({u} V) au-dessus de la tension actuelle ({v} V).")
                        .format(u=f"{uv:g}", v=f"{vbus:.1f}")))
    if ov is not None and ov > 56:
        out.append(("warn", T("Coupure tension haute au-delà de 56 V : au-dessus de la tension maxi de la carte.")))
    if g("config.enable_brake_resistor") == 0:
        out.append(("warn", T("Résistance de freinage désactivée : l'énergie de freinage repart dans l'alimentation "
                              "(surtension possible, dangereux pour une batterie pleine).")))
    br = g("config.brake_resistance")
    if g("config.enable_brake_resistor") == 1 and br is not None and not (0.5 <= br <= 50):
        out.append(("warn", T("Valeur de résistance de freinage inhabituelle ({r} Ω) : mets la valeur gravée dessus.")
                    .format(r=f"{br:g}")))
    il, rng = g("axis0.motor.config.current_lim"), g("axis0.motor.config.requested_current_range")
    if il is not None and rng is not None and il > rng * 0.95:
        out.append(("warn", T("Courant maximum ({i} A) trop près de la gamme de mesure ({r} A) : erreur de "
                              "saturation possible.").format(i=f"{il:g}", r=f"{rng:g}")))
    cc, r, vmax = g("axis0.motor.config.calibration_current"), g("axis0.motor.config.phase_resistance"), \
        g("axis0.motor.config.resistance_calib_max_voltage")
    if cc and r and vmax and cc * r > vmax:
        out.append(("warn", T("Courant de calibration × résistance ({x} V) au-dessus de la tension max de "
                              "calibration ({m} V) : la calibration échouera.").format(x=f"{cc * r:.2f}", m=f"{vmax:g}")))
    if g("axis0.motor.config.pre_calibrated") == 1 and not r:
        out.append(("warn", T("Moteur marqué calibré alors qu'aucune résistance de phase n'est enregistrée.")))
    kt, mt = g("axis0.motor.config.torque_constant"), g("axis.maxtorque")
    if kt and il and mt and mt > kt * il * 1.02:
        out.append(("warn", T("Couple maximum du volant ({m} N·m) au-dessus de ce que permet le courant maximum "
                              "(Kt × I = {k} N·m) : les fortes forces seront écrêtées.")
                    .format(m=f"{mt:g}", k=f"{kt * il:.2f}")))
    return out


# ======================================================================
#  Onglet
# ======================================================================
PAGES = [
    (T("Volant"), [P.FFB_RANGE, P.FFB_ALWAYS, P.FFB_STOPS, P.FFB_CURVE]),
    (T("Effets du jeu"), [P.FX_GAINS, P.FX_FILT, P.FX_EQ]),
    (T("Moteur et codeur"), [P.MOT, P.MOT_CAL, P.ENC, P.CTRL, P.BOOT]),
    (T("Alimentation"), [P.PWR, P.BRAKE, P.TEMP]),
]
GROUP_HINTS = {
    P.FFB_ALWAYS: T("Ces effets agissent toujours, jeu lancé ou non (0 = désactivé, 255 = maximum)."),
    P.FX_GAINS: T("Proportion de chaque effet envoyé par le jeu (255 = 100 %)."),
    P.FX_FILT: T("Filtres appliqués aux effets du jeu. Q : 0,70 = réponse plate."),
    P.BOOT: T("Ce que fait la carte à chaque allumage. Avec un codeur incrémental sans index : moteur déjà "
              "calibré, calage du codeur, puis boucle fermée."),
    P.PWR: T("Toutes ces protections dépendent du pont diviseur : vérifie une fois la tension affichée au "
             "multimètre."),
    P.MOT_CAL: T("Résistance et inductance sont mesurées par la calibration moteur (onglet Mise en route)."),
}


class SettingsTab(QWidget):
    dirty_changed = Signal(bool, bool)       # réglages non mémorisés : (volant/effets, ODrive)

    def __init__(self, board, parent=None):
        super().__init__(parent)
        self.b = board
        self.rows: dict[str, ParamRow] = {}
        self.pending: dict[str, object] = {}      # chemin → valeur brute à envoyer
        self.inflight: dict[str, object] = {}
        self.unsaved = {"ffb": set(), "odrive": set()}
        self.vbus = None
        self.ident = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 8)
        root.setSpacing(8)
        top = QHBoxLayout()
        self.live = QCheckBox(T("Appliquer en direct les réglages du volant et des effets"))
        self.live.setChecked(True)
        self.cards = []
        self.adv = QCheckBox(T("Réglages avancés"))
        self.adv.setToolTip(T("Affiche aussi les réglages rarement utiles (filtres détaillés, égaliseur, courbe, "
                              "boucles de régulation, températures, entrées GPIO). Leurs valeurs d'usine conviennent."))
        try:
            self.adv.setChecked(i18n.settings().value("advanced", "false") == "true")
        except Exception:
            pass
        self.live.setToolTip(T("Les réglages volant/effets sont envoyés dès qu'on les change (comme l'outil web). "
                               "Les réglages ODrive (moteur, codeur, alimentation) attendent « Appliquer »."))
        top.addWidget(self.live)
        top.addSpacing(16)
        top.addWidget(self.adv)
        top.addStretch()
        self.progress = QLabel("")
        self.progress.setObjectName("hint")
        top.addWidget(self.progress)
        self.b_read = QPushButton(T("Relire la carte"))
        self.b_read.clicked.connect(self.b.read_all)
        top.addWidget(self.b_read)
        self.b_revert = QPushButton(T("Annuler les modifications"))
        self.b_revert.clicked.connect(self.revert)
        top.addWidget(self.b_revert)
        self.b_apply = QPushButton(T("Appliquer"))
        self.b_apply.setObjectName("primary")
        self.b_apply.setToolTip(T("Envoie les modifications en attente dans la carte (sans les mémoriser)."))
        self.b_apply.clicked.connect(self._flush)
        top.addWidget(self.b_apply)
        root.addLayout(top)

        self.tabs = TabPages()          # onglets sans le mode « document » de Qt (dessin glitché sous Windows)
        for title, groups in PAGES:
            self.tabs.addTab(self._page(groups), title)
        self.gpio_index = self.tabs.addTab(self._gpio_page(), T("Entrées GPIO"))
        self.tabs.addTab(self._board_page(), T("Carte et profils"))
        root.addWidget(self.tabs, 1)
        self.adv.toggled.connect(self._show_adv)
        self._show_adv(self.adv.isChecked())

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(self._flush_live)

        self.b.values.connect(self.on_values)
        self.b.write_done.connect(self.on_write_done)
        self.b.progress.connect(lambda i, n: self.progress.setText(
            "" if i >= n else T("Lecture {i}/{n}…").format(i=i, n=n)))
        self.b.telemetry.connect(self._on_tm)
        self.b.link_changed.connect(self._on_link)
        self._update_buttons()

    def _show_adv(self, on):
        """Mode simple : masque les réglages avancés (et les cartes qui n'en contiennent que)."""
        for c, rows in self.cards:
            any_vis = False
            for r in rows:
                vis = on or r.f.path not in P.ADVANCED
                r.setVisible(vis)
                any_vis |= vis
            c.setVisible(any_vis)
        self.tabs.setTabVisible(self.gpio_index, on)
        try:
            i18n.settings().setValue("advanced", "true" if on else "false")
        except Exception:
            pass

    # ---------------------------------------------------------------- construction
    def _scroll(self, inner):
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setWidget(inner)
        return sc

    def _row(self, f, label=None, lw=250):
        r = ParamRow(f, label, lw)
        r.edited.connect(self.on_edit_user)
        self.rows[f.path] = r
        return r

    def _page(self, groups):
        inner = QWidget()
        cols = QHBoxLayout(inner)
        cols.setContentsMargins(0, 8, 6, 8)
        cols.setSpacing(12)
        left, right = QVBoxLayout(), QVBoxLayout()
        left.setSpacing(12)
        right.setSpacing(12)
        # répartition équilibrée par nombre de lignes
        sizes = [sum(1 for f in P.FIELDS if f.group == g) + 2 for g in groups]
        tot, acc = sum(sizes), 0
        for g, n in zip(groups, sizes):
            c, l = card(P.G[g])
            if g in GROUP_HINTS:
                l.addWidget(hint(GROUP_HINTS[g]))
            rows = []
            for f in P.FIELDS:
                if f.group == g:
                    r = self._row(f)
                    rows.append(r)
                    l.addWidget(r)
            self.cards.append((c, rows))
            if g == P.FX_EQ:
                self.eq_info = hint("")
                l.addWidget(self.eq_info)
            if g == P.PWR:
                g2 = QGridLayout()
                self.s_vbus = StatRow(T("Tension mesurée"), "V")
                self.s_ibus = StatRow(T("Courant tiré"), "A")
                self.s_ibrk = StatRow(T("Courant dans la résistance"), "A")
                self.s_syserr = QLabel("")
                self.s_syserr.setWordWrap(True)
                for i, w in enumerate((self.s_vbus, self.s_ibus, self.s_ibrk)):
                    g2.addWidget(w, i, 0)
                l.addLayout(g2)
                l.addWidget(self.s_syserr)
            (left if acc < tot / 2 else right).addWidget(c)
            acc += n
        left.addStretch()
        right.addStretch()
        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        return self._scroll(inner)

    def _gpio_page(self):
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 8, 6, 8)
        lay.setSpacing(12)
        c, l = card(T("Entrées GPIO du connecteur"))
        l.addWidget(hint(T("Chaque GPIO peut devenir un bouton (contact vers GND), un axe analogique (0–3,3 V, "
                           "GPIO 1 à 4 seulement) ou un bouton de recentrage. GPIO 1 et 2 servent aussi à l'UART A "
                           "de l'ODrive : désactive-le (config.enable_uart_a) avant de t'en servir. Ne branche "
                           "jamais plus de 3,3 V.")))
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        for j, h in enumerate([T("GPIO"), T("Mode"), T("N° bouton / axe"), T("Inverser"), T("Mini"), T("Maxi"),
                               T("Lecture brute")]):
            lab = QLabel(h)
            lab.setObjectName("hint")
            lab.setAlignment(Qt.AlignCenter if j else Qt.AlignLeft)
            g.addWidget(lab, 0, j)
        self.gpio_cur = {}
        for i, pin in enumerate(P.GPIO_PINS):
            g.addWidget(QLabel(f"GPIO {pin}"), i + 1, 0)
            for j, n in enumerate(P.GPIO_FIELDS):
                f = P.gpio_field(pin, n)
                r = self._row(f, "", 0)
                r.lbl.hide()
                if n in ("amin", "amax") and pin not in P.GPIO_ANALOG:
                    r.setVisible(False)
                g.addWidget(r, i + 1, j + 1)
            cur = QLabel("—")
            cur.setObjectName("midValue")
            self.gpio_cur[pin] = cur
            g.addWidget(cur, i + 1, len(P.GPIO_FIELDS) + 1)
        l.addLayout(g)
        b = QPushButton(T("Lire les entrées maintenant"))
        b.clicked.connect(self.read_gpio_now)
        hl = QHBoxLayout()
        hl.addWidget(b)
        hl.addStretch()
        l.addLayout(hl)
        lay.addWidget(c)
        c, l = card(T("Traitement des axes analogiques"))
        for f in P.GPIO_GLOBAL:
            l.addWidget(self._row(f))
        lay.addWidget(c)
        lay.addStretch()
        return self._scroll(inner)

    def _board_page(self):
        inner = QWidget()
        cols = QHBoxLayout(inner)
        cols.setContentsMargins(0, 8, 6, 8)
        cols.setSpacing(12)
        left, right = QVBoxLayout(), QVBoxLayout()
        c, l = card(T("Carte"))
        self.id_rows = {}
        for key, lab in (("hw", T("Matériel")), ("fw", T("Base ODrive")), ("hwtype", T("Firmware")),
                         ("serial", T("N° de série")), ("uid", T("Identifiant STM32")),
                         ("zero", T("Décalage du centre")), ("port", T("Port série"))):
            s = StatRow(lab)
            s.v.setMinimumWidth(40)
            self.id_rows[key] = s
            l.addWidget(s)
        left.addWidget(c)
        c, l = card(T("Contrôles de cohérence"))
        l.addWidget(hint(T("Vérifications faites sur les valeurs de la carte (et les modifications en attente).")))
        self.checks_lbl = QLabel(T("Réglages pas encore lus."))
        self.checks_lbl.setWordWrap(True)
        self.checks_lbl.setTextFormat(Qt.RichText)
        l.addWidget(self.checks_lbl)
        left.addWidget(c)
        left.addStretch()

        c, l = card(T("Profils"))
        l.addWidget(hint(T("Fichier JSON au même format que l'export de l'outil web Odrive-Wheel : les deux sont "
                           "interchangeables. L'import ne fait que préparer les modifications : tu les vois en "
                           "orange avant de cliquer « Appliquer ».")))
        hl = QHBoxLayout()
        b1 = QPushButton(T("Exporter la configuration…"))
        b1.clicked.connect(self.export_profile)
        b2 = QPushButton(T("Importer un profil…"))
        b2.clicked.connect(self.import_profile)
        hl.addWidget(b1)
        hl.addWidget(b2)
        hl.addStretch()
        l.addLayout(hl)
        self.import_lbl = hint("")
        l.addWidget(self.import_lbl)
        right.addWidget(c)
        c, l = card(T("Zone dangereuse"))
        l.addWidget(hint(T("Effacer la configuration ODrive remet tous les réglages moteur, codeur et alimentation "
                           "d'usine, puis redémarre. Exporte d'abord ta configuration.")))
        b3 = QPushButton(T("Effacer la configuration ODrive…"))
        b3.setObjectName("danger")
        b3.clicked.connect(self.erase)
        hl = QHBoxLayout()
        hl.addWidget(b3)
        hl.addStretch()
        l.addLayout(hl)
        right.addWidget(c)
        right.addStretch()
        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        return self._scroll(inner)

    # ---------------------------------------------------------------- lecture
    def on_values(self, vals: dict, tag: str):
        for p, txt in vals.items():
            r = self.rows.get(p)
            if r is None:
                continue
            if p in self.inflight:
                continue                    # la relecture d'écriture fera foi
            keep = p in self.pending
            r.set_device(txt)
            if keep and r.read_ok:
                r.set_value(self.pending[p])
                r._style("modified")
            elif tag == "all":
                self.pending.pop(p, None)
        if tag == "all":
            self.unsaved = {"ffb": set(), "odrive": set()}
            self.dirty_changed.emit(False, False)
        for k in ("hw_version_major", "hw_version_minor", "hw_version_variant", "fw_version_major",
                  "fw_version_minor", "fw_version_revision", "serial_number", "sys.hwtype", "sys.uid",
                  "axis.zeroofs", "error"):
            if k in vals:
                self.ident[k] = vals[k]
        self._show_ident()
        if any(k in vals for k in P.EQ_INFO):
            fq = {k: vals.get(k) for k in P.EQ_INFO}
            if all(fq.values()):
                self.eq_info.setText(T("Bandes du firmware : poids {a} Hz (Q {qa}), châssis {b} Hz (Q {qb}), "
                                       "route {c} Hz (Q {qc}).").format(
                    a=fq["axis.eqweightfreq"], b=fq["axis.eqchassisfreq"], c=fq["axis.eqroadfreq"],
                    qa=fq["axis.eqweightq"], qb=fq["axis.eqchassisq"], qc=fq["axis.eqroadq"]))
        if tag == "gpio":
            for pin, lab in self.gpio_cur.items():
                v = vals.get(f"gpio.{pin}.cur")
                lab.setText(v if v is not None else "—")
        self._update_checks()
        self._update_buttons()

    def _show_ident(self):
        g = self.ident.get
        if g("hw_version_major") is not None:
            self.id_rows["hw"].set(f"ODrive v{g('hw_version_major')}.{g('hw_version_minor')}-{g('hw_version_variant')}V")
        if g("fw_version_major") is not None:
            v = f"{g('fw_version_major')}.{g('fw_version_minor')}.{g('fw_version_revision')}"
            if v == "0.0.0":
                # Odrive-Wheel fige la version ODrive à 0.0.0 dans ses sources (autogen/version.c)
                self.id_rows["fw"].set("0.5.6")
                self.id_rows["fw"].setToolTip(T("La carte répond 0.0.0 : Odrive-Wheel ne renseigne pas la version "
                                                "ODrive (fichier figé dans ses sources). Sa base est la 0.5.6."))
            else:
                self.id_rows["fw"].set(v)
        for k, key in (("hwtype", "sys.hwtype"), ("uid", "sys.uid")):
            if g(key) is not None:
                self.id_rows[k].set(g(key))
        sn = g("serial_number")
        if sn is not None:
            # la réponse ASCII de l'ODrive est limitée à 9 caractères : un n° plus long arrive tronqué
            self.id_rows["serial"].set(sn + ("…" if len(sn) >= 9 else ""))
            self.id_rows["serial"].setToolTip(T("Réponse limitée à 9 caractères par le firmware : n° tronqué.")
                                              if len(sn) >= 9 else "")
        if g("axis.zeroofs") is not None:
            self.id_rows["zero"].set(f"{P.to_float(g('axis.zeroofs')) or 0:+.1f} °")
        se = P.to_float(g("error"))
        if se is not None and hasattr(self, "s_syserr"):
            errs = P.decode("system", int(se))
            self.s_syserr.setText("\n".join(f"✖ {n} — {d}" for n, d in errs) if errs else T("Aucune erreur système."))
            self.s_syserr.setStyleSheet(f"color: {C['bad'] if errs else C['ok']};")

    def read_gpio_now(self):
        self.b.read([f"gpio.{p}.cur" for p in P.GPIO_PINS], "gpio")

    # ---------------------------------------------------------------- modifications
    def on_edit_user(self, path, raw):
        r = self.rows[path]
        if r.modified():
            self.pending[path] = raw
        else:
            self.pending.pop(path, None)
        if self.live.isChecked() and r.f.store == "ffb" and not r.f.critical:
            self._debounce.start()
        self._update_checks()
        self._update_buttons()

    def on_edit(self, path, raw):
        """Modification venant d'un autre onglet (Mise en route, import)."""
        r = self.rows.get(path)
        if r is None or not r.read_ok:
            return False
        r.set_value(raw)
        if r.modified():
            self.pending[path] = r.value()
            r._style("modified")
        else:
            self.pending.pop(path, None)
        self._update_checks()
        self._update_buttons()
        return True

    def _flush_live(self):
        paths = [p for p in self.pending if self.rows[p].f.store == "ffb" and not self.rows[p].f.critical]
        self._send(paths)

    def _flush(self) -> bool:
        """Envoie les modifications en attente ; False si rien n'est parti (rien à envoyer, carte absente, annulé)."""
        paths = list(self.pending)
        if not paths:
            return False
        if not self.b.serial_ok:
            QMessageBox.warning(self, T("Appliquer"), T("La carte n'est pas connectée."))
            return False
        crit = [p for p in paths if self.rows[p].f.critical and self.rows[p].f.store == "odrive"]
        st = self.b.state
        if crit and st not in (P.IDLE, None):
            names = "\n".join("• " + self.rows[p].f.label for p in crit)
            if QMessageBox.question(self, T("Moteur actif"),
                                    T("Ces réglages ne doivent être changés que moteur au repos :\n{n}\n\nMettre "
                                      "le moteur au repos (il devient libre) puis appliquer ?").format(n=names)) \
                    != QMessageBox.Yes:
                return False
            self.b.request_state(P.IDLE)
        bad = [x for x in safety_checks(self._effective(), self.vbus) if x[0] == "bad"]
        if bad and QMessageBox.warning(self, T("Contrôles de cohérence"),
                                       T("Problèmes détectés :\n\n{p}\n\nAppliquer quand même ?").format(
                                           p="\n\n".join("• " + t for _l, t in bad)),
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return False
        # ordre : alimentation d'abord, puis le reste
        paths.sort(key=lambda p: (0 if p.startswith(("sys.vbusdiv", "config.")) else 1, p))
        self._send(paths)
        return True

    def _send(self, paths):
        for p in paths:
            raw = self.pending.pop(p, None)
            if raw is None:
                continue
            self.inflight[p] = raw
            self.rows[p]._style("pending")
            self.b.write(p, raw)
        self._update_buttons()

    def on_write_done(self, path, ok, readback, msg):
        r = self.rows.get(path)
        want = self.inflight.pop(path, None)
        if r is None:
            return
        if ok:
            r.set_device(readback)
            if r.read_ok and want is not None and not r.f.same(r.device, want):
                r._style("error")
                r.dot.setToolTip(T("La carte a retenu {v} au lieu de la valeur demandée (borne du firmware).")
                                 .format(v=readback))
            else:
                r._style("saved_needed")
            self.unsaved[r.f.store].add(path)
            self.dirty_changed.emit(bool(self.unsaved["ffb"]), bool(self.unsaved["odrive"]))
            if path == "axis.range":
                self.b.read(["axis.range"], "range")
        else:
            r.error(msg)
        self._update_checks()
        self._update_buttons()

    def revert(self):
        for p in list(self.pending):
            r = self.rows[p]
            r.set_value(r.device)
            r._style("normal")
        self.pending.clear()
        self._update_checks()
        self._update_buttons()

    def saved(self, store):
        """Appelé après une mémorisation réussie."""
        for p in self.unsaved.get(store, set()):
            r = self.rows.get(p)
            if r and r.state == "saved_needed":
                r._style("normal")
        self.unsaved[store] = set()
        self.dirty_changed.emit(bool(self.unsaved["ffb"]), bool(self.unsaved["odrive"]))

    def _update_buttons(self):
        n = len(self.pending)
        self.b_apply.setEnabled(n > 0 and self.b.serial_ok)
        self.b_apply.setText(T("Appliquer ({n})").format(n=n) if n else T("Appliquer"))
        self.b_revert.setEnabled(n > 0)
        self.b_read.setEnabled(self.b.serial_ok)

    # ---------------------------------------------------------------- cohérence
    def device_values(self):
        return {p: r.device for p, r in self.rows.items() if r.read_ok}

    def _effective(self):
        v = self.device_values()
        v.update(self.pending)
        return v

    def _update_checks(self):
        if not any(r.read_ok for r in self.rows.values()):
            return
        res = safety_checks(self._effective(), self.vbus)
        if not res:
            self.checks_lbl.setText(f'<span style="color:{C["ok"]}">✔ ' + T("Aucun problème détecté.") + "</span>")
        else:
            self.checks_lbl.setText("<br><br>".join(
                f'<span style="color:{C["bad"] if lv == "bad" else C["warn"]}">{"✖" if lv == "bad" else "⚠"} {t}</span>'
                for lv, t in res))

    def _on_tm(self, batch):
        tm = batch[-1]
        # les erreurs système (tension, courant bus) ne sont pas dans le rapport HID : on les lit quand le
        # moteur signale SYSTEM_LEVEL
        now = time.perf_counter()
        if tm.motor_err & 0x01000000 and self.b.serial_ok and now - getattr(self, "_t_syserr", 0) > 1.5:
            self._t_syserr = now
            self.b.read(["error"], "syserr")
        new = tm.vbus
        changed = self.vbus is None or abs(new - self.vbus) > 0.5
        self.vbus = new
        if hasattr(self, "s_vbus"):
            self.s_vbus.set(f"{tm.vbus:.2f}")
            self.s_ibus.set(f"{tm.ibus:+.2f}")
            self.s_ibrk.set(f"{tm.ibrake:.2f}")
        if changed:
            self._update_checks()

    def _on_link(self, info):
        if info.get("serial") is True:
            self.id_rows["port"].set(str(info.get("port")))
        elif info.get("serial") is False:
            self.id_rows["port"].set("—")
            self.inflight.clear()
        self._update_buttons()

    # ---------------------------------------------------------------- profils
    def export_profile(self):
        # lecture seule comprise (version, n° de série…), comme l'export de l'outil web Odrive-Wheel
        vals = {p: r.f.fmt(r.device) for p, r in self.rows.items() if r.read_ok}
        if not vals:
            QMessageBox.information(self, T("Exporter"), T("Rien à exporter : réglages pas encore lus."))
            return
        fn, _ = QFileDialog.getSaveFileName(self, T("Exporter la configuration"),
                                            time.strftime("odrive_config_%Y-%m-%d_%H-%M.json"), "JSON (*.json)")
        if not fn:
            return
        if not save_json(self, fn, vals, indent=2, ensure_ascii=False):
            return
        self.import_lbl.setText(T("Exporté : {f} ({n} réglages).").format(f=fn, n=len(vals)))

    def import_profile(self):
        fn, _ = QFileDialog.getOpenFileName(self, T("Importer un profil"), "", "JSON (*.json)")
        if not fn:
            return
        try:
            with open(fn, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError(T("format inattendu"))
        except Exception as e:
            QMessageBox.warning(self, T("Importer"), T("Fichier illisible : {e}").format(e=e))
            return
        self.apply_profile(data, fn)

    def apply_profile(self, data: dict, name=""):
        changed, same, unknown, unread, refused = 0, 0, [], [], []
        for p, txt in data.items():
            r = self.rows.get(p)
            if r is not None and r.f.ro:
                continue                    # lecture seule (version, n° de série…) : exportée, jamais réécrite
            if r is None:
                unknown.append(p)
                continue
            if not r.read_ok:
                unread.append(p)
                continue
            v = r.f.parse(str(txt))
            if v is None:
                refused.append(f"{p} = {txt}")
                continue
            # sécurité : jamais « calage conservé » avec un codeur incrémental sans index
            if p == "axis0.encoder.config.pre_calibrated" and v == 1:
                eff = self._effective()
                mode = P.BY_PATH["axis0.encoder.config.mode"].parse(str(data.get("axis0.encoder.config.mode", ""))) \
                    if "axis0.encoder.config.mode" in data else eff.get("axis0.encoder.config.mode")
                idx = P.BY_PATH["axis0.encoder.config.use_index"].parse(str(data.get("axis0.encoder.config.use_index", ""))) \
                    if "axis0.encoder.config.use_index" in data else eff.get("axis0.encoder.config.use_index")
                if mode == 0 and idx == 0:
                    refused.append(T("{p} = 1 ignoré (codeur incrémental sans index)").format(p=p))
                    continue
            if r.f.same(v, r.device):
                same += 1
                continue
            self.on_edit(p, v)
            changed += 1
        msg = T("{f} : {c} modification(s) préparée(s), {s} déjà identique(s).").format(f=name, c=changed, s=same)
        if refused:
            msg += "\n" + T("Ignorés : {l}").format(l="; ".join(refused))
        if unread:
            msg += "\n" + T("Non lus dans la carte : {n}").format(n=len(unread))
        if unknown:
            msg += "\n" + T("Non gérés par SimForge (laissés tels quels) : {n}").format(n=len(unknown))
        self.import_lbl.setText(msg)
        self._update_checks()
        if changed:
            self.import_lbl.setText(msg + "\n" + T("Vérifie les valeurs en orange, puis « Appliquer » et "
                                                     "« Enregistrer »."))

    def erase(self):
        if QMessageBox.warning(self, T("Effacer la configuration ODrive"),
                               T("Tous les réglages moteur, codeur et alimentation vont être remis d'usine et la carte "
                                 "va redémarrer. Les réglages du volant et des effets ne sont pas touchés.\n\n"
                                 "Continuer ?"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.b.request_state(P.IDLE)
        self.b.system("se")
