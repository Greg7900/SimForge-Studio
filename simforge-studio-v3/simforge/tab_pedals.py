"""Pages Pédales : réglages (avec la courbe de force) et état en direct de chaque pédale active ChrGri."""
from __future__ import annotations

import json
import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
                               QCheckBox, QDoubleSpinBox, QSpinBox, QScrollArea, QMessageBox, QFileDialog,
                               QPlainTextEdit)

from . import ped_protocol as PP
from .i18n import T
from .theme import C
from .widgets import card, hint, repolish, StatRow, AxisBar

pg.setConfigOptions(antialias=False, background=C["panel"], foreground=C["dim"])


def _pct(v):
    return (v or 0) / 65535 * 100


class PRow(QWidget):
    """Ligne d'un réglage de pédale (valeur brute ↔ valeur affichée)."""
    edited = Signal()

    def __init__(self, f: PP.PField):
        super().__init__()
        self.f = f
        self.device = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        self.lbl = QLabel(f.label)
        self.lbl.setMinimumWidth(max(230, self.lbl.sizeHint().width()))
        self.setToolTip((f.tip + "\n\n" if f.tip else "") + f.name)
        lay.addWidget(self.lbl)
        lay.addStretch(1)
        if f.kind == "bool":
            self.ed = QCheckBox()
            self.ed.toggled.connect(self._ch)
        elif f.kind == "enum":
            self.ed = QComboBox()
            for v, t in f.items:
                self.ed.addItem(t, v)
            self.ed.currentIndexChanged.connect(self._ch)
        else:
            self.ed = QDoubleSpinBox()
            self.ed.setDecimals(f.dec)
            self.ed.setRange(f.lo, f.hi)
            self.ed.setSingleStep(10 ** -f.dec if f.dec else 1)
            self.ed.setKeyboardTracking(False)
            self.ed.setAlignment(Qt.AlignRight)
            self.ed.setMinimumWidth(110)
            if f.unit:
                self.ed.setSuffix(" " + f.unit)
            self.ed.valueChanged.connect(self._ch)
        lay.addWidget(self.ed)
        self._block = False

    def _ch(self, *_):
        if self._block:
            return
        self._mark()
        self.edited.emit()

    def value(self):
        f = self.f
        if f.kind == "bool":
            return 1 if self.ed.isChecked() else 0
        if f.kind == "enum":
            d = self.ed.currentData()
            return int(d) if d is not None else self.device
        v = self.ed.value() / f.scale
        return float(v) if f.kind == "float" else int(round(v))

    def set(self, raw):
        f = self.f
        self._block = True
        if f.kind == "bool":
            self.ed.setChecked(bool(raw))
        elif f.kind == "enum":
            i = self.ed.findData(int(raw))
            if i < 0:
                self.ed.addItem(T("Valeur inconnue ({v})").format(v=raw), int(raw))
                i = self.ed.count() - 1
            self.ed.setCurrentIndex(i)
        else:
            d = raw * f.scale
            if d < self.ed.minimum() or d > self.ed.maximum():
                self.ed.setRange(min(d, self.ed.minimum()), max(d, self.ed.maximum()))
            self.ed.setValue(d)
        self._block = False
        self._mark()

    def set_device(self, raw):
        self.device = raw
        self.set(raw)

    def modified(self):
        if self.device is None:
            return False
        v = self.value()
        if self.f.kind == "float":
            return abs(v - self.device) > 10 ** -(self.f.dec + 1)
        return v != self.device

    def _mark(self):
        m = "true" if self.modified() else "false"
        if self.ed.property("modified") != m:
            self.ed.setProperty("modified", m)
            repolish(self.ed)


class CurveEditor(QWidget):
    """Courbe force/course (jusqu'à 11 points) : tableau de valeurs + graphique, avec la position en direct."""
    edited = Signal()

    def __init__(self, title, xs_keys, ys_keys, n_key, xlabel, ylabel):
        super().__init__()
        self.xs_keys, self.ys_keys, self.n_key = xs_keys, ys_keys, n_key
        self.device = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.addWidget(QLabel(T("Nombre de points")))
        self.n = QSpinBox()
        self.n.setRange(2, 11)
        self.n.valueChanged.connect(self._n_changed)
        top.addWidget(self.n)
        top.addSpacing(12)
        top.addWidget(QLabel(T("Modèle")))
        self.preset = QComboBox()
        self.preset.addItems([T("— choisir —"), T("Linéaire"), T("Progressive (frein)"), T("Très progressive"),
                              T("Dégressive")])
        self.preset.currentIndexChanged.connect(self._preset)
        top.addWidget(self.preset)
        top.addStretch()
        lay.addLayout(top)
        self.plot = pg.PlotWidget()
        self.plot.setMinimumHeight(170)
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel("bottom", xlabel, "%")
        self.plot.setLabel("left", ylabel, "%")
        self.plot.setXRange(0, 100, padding=0.02)
        self.plot.setYRange(0, 100, padding=0.02)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setMenuEnabled(False)
        for ax in ("left", "bottom"):
            self.plot.getAxis(ax).enableAutoSIPrefix(False)
        self.curve = self.plot.plot(pen=pg.mkPen(C["accent"], width=2), symbol="o", symbolSize=7,
                                    symbolBrush=C["accent"])
        self.live = pg.ScatterPlotItem(size=12, brush=pg.mkBrush(C["blue"]), pen=None)
        self.plot.addItem(self.live)
        lay.addWidget(self.plot, 1)
        g = QGridLayout()
        g.addWidget(QLabel(xlabel + " %"), 0, 0)
        g.addWidget(QLabel(ylabel + " %"), 1, 0)
        self.sx, self.sy = [], []
        for i in range(11):
            a, b = QSpinBox(), QSpinBox()
            for s in (a, b):
                s.setRange(0, 100)
                # NoButtons + la feuille de style masquait le chiffre : flèches gardées mais réduites à 0 px
                s.setStyleSheet("QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }")
                s.setAlignment(Qt.AlignCenter)
                s.setKeyboardTracking(False)
                s.setMinimumWidth(46)
                s.valueChanged.connect(self._val)
            g.addWidget(a, 0, i + 1)
            g.addWidget(b, 1, i + 1)
            self.sx.append(a)
            self.sy.append(b)
        lay.addLayout(g)
        self._block = False

    def _n_changed(self, n):
        for i in range(11):
            self.sx[i].setVisible(i < n)
            self.sy[i].setVisible(i < n)
        if not self._block:
            # répartit les abscisses régulièrement quand on change le nombre de points
            self._block = True
            ys = self._interp([i * 100 / (n - 1) for i in range(n)])
            for i in range(n):
                self.sx[i].setValue(round(i * 100 / (n - 1)))
                self.sy[i].setValue(round(ys[i]))
            self._block = False
            self._val()
        self._draw()

    def _interp(self, xs):
        n0 = self.n.value() if self.device else 0
        px = [s.value() for s in self.sx[:max(2, n0)]]
        py = [s.value() for s in self.sy[:max(2, n0)]]
        out = []
        for x in xs:
            if not px or px[-1] == px[0]:
                out.append(x)
                continue
            for i in range(1, len(px)):
                if x <= px[i] or i == len(px) - 1:
                    x0, x1, y0, y1 = px[i - 1], px[i], py[i - 1], py[i]
                    out.append(y0 + (y1 - y0) * ((x - x0) / (x1 - x0) if x1 != x0 else 0))
                    break
        return out

    def _preset(self, i):
        if i <= 0:
            return
        n = self.n.value()
        xs = [k * 100 / (n - 1) for k in range(n)]
        fn = {1: lambda x: x, 2: lambda x: 100 * (x / 100) ** 1.6, 3: lambda x: 100 * (x / 100) ** 2.4,
              4: lambda x: 100 * (x / 100) ** 0.65}[i]
        self._block = True
        for k in range(n):
            self.sx[k].setValue(round(xs[k]))
            self.sy[k].setValue(round(fn(xs[k])))
        self._block = False
        self.preset.blockSignals(True)
        self.preset.setCurrentIndex(0)
        self.preset.blockSignals(False)
        self._val()

    def _val(self, *_):
        if self._block:
            return
        self._draw()
        self.edited.emit()

    def _draw(self):
        n = self.n.value()
        self.curve.setData([s.value() for s in self.sx[:n]], [s.value() for s in self.sy[:n]])

    def set_cfg(self, cfg):
        self._block = True
        n = max(2, min(11, cfg[self.n_key]))
        self.n.setValue(n)
        for i in range(11):
            self.sx[i].setValue(cfg[self.xs_keys[i]])
            self.sy[i].setValue(cfg[self.ys_keys[i]])
            self.sx[i].setVisible(i < n)
            self.sy[i].setVisible(i < n)
        self._block = False
        self.device = {k: cfg[k] for k in self.xs_keys + self.ys_keys + [self.n_key]}
        self._draw()

    def values(self):
        d = {self.n_key: self.n.value()}
        for i in range(11):
            d[self.xs_keys[i]] = self.sx[i].value() if i < self.n.value() else 0
            d[self.ys_keys[i]] = self.sy[i].value() if i < self.n.value() else 0
        return d

    def problems(self):
        n = self.n.value()
        xs = [s.value() for s in self.sx[:n]]
        if xs[0] != 0 or xs[-1] != 100:
            return T("la courbe doit commencer à 0 % et finir à 100 % de course")
        if any(b <= a for a, b in zip(xs, xs[1:])):
            return T("les positions de la courbe doivent être croissantes")
        return ""

    def modified(self):
        return self.device is not None and self.values() != {
            k: (self.device[k] if (k == self.n_key or self._idx(k) < self.n.value()) else 0) for k in self.device}

    def _idx(self, k):
        return int(k[-5:-3])

    def set_live(self, x, y):
        self.live.setData([x], [y])


class PedalsTab(QWidget):
    def __init__(self, mgr, parent=None):
        super().__init__(parent)
        self.m = mgr
        self.port = None
        self.cfg = None                 # dernière config lue (brute, complète)
        self.rows: dict[str, PRow] = {}
        self.hist = deque(maxlen=1500)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 8)
        root.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(QLabel(T("Pédale")))
        self.sel = QComboBox()
        self.sel.setMinimumWidth(260)
        self.sel.currentIndexChanged.connect(self._select)
        top.addWidget(self.sel)
        self.status = QLabel(T("Aucune pédale détectée"))
        self.status.setObjectName("hint")
        self.status.setWordWrap(True)
        self.status.setMinimumWidth(120)
        from PySide6.QtWidgets import QSizePolicy
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addStretch(1)
        self.adv = QCheckBox(T("Réglages avancés"))
        self.adv.toggled.connect(self._show_adv)
        top.addWidget(self.adv)
        self.b_beep = QPushButton(T("Identifier (bip)"))
        self.b_beep.clicked.connect(lambda: self.m.action(self.port, T("bip d'identification"),
                                                         systemAction_u8=PP.ACT_BEEP))
        top.addWidget(self.b_beep)
        self.b_read = QPushButton(T("Relire"))
        self.b_read.clicked.connect(lambda: self.m.request_config(self.port))
        top.addWidget(self.b_read)
        self.b_apply = QPushButton(T("Appliquer"))
        self.b_apply.setToolTip(T("Envoie les réglages à la pédale sans les mémoriser (perdus au redémarrage)."))
        self.b_apply.clicked.connect(lambda: self.send(False))
        top.addWidget(self.b_apply)
        self.b_save = QPushButton(T("Enregistrer dans la pédale"))
        self.b_save.setObjectName("primary")
        self.b_save.clicked.connect(lambda: self.send(True))
        top.addWidget(self.b_save)
        root.addLayout(top)
        root.addWidget(self.status)

        body = QHBoxLayout()
        body.setSpacing(12)
        # ------------------------------------------- réglages
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 6, 0)
        il.setSpacing(12)
        self.cards = []
        for g in (PP.G_MAIN, PP.G_FX, PP.G_MECH, PP.G_CTRL):
            c, l = card(g)
            rows = []
            for f in PP.PFIELDS:
                if f.group == g:
                    r = PRow(f)
                    r.edited.connect(self._dirty)
                    self.rows[f.name] = r
                    rows.append(r)
                    l.addWidget(r)
            if g == PP.G_FX:
                hb = QHBoxLayout()
                b = QPushButton(T("Tester l'ABS (1 s)"))
                b.setToolTip(T("Déclenche l'effet ABS pendant 1 seconde, sans jeu : appuie sur la pédale."))
                b.clicked.connect(self.test_abs)
                hb.addWidget(b)
                hb.addStretch()
                l.addLayout(hb)
                l.addWidget(hint(T("En jeu, les effets (ABS, régime, patinage…) ne marchent que si un logiciel "
                                   "envoie la télémétrie du jeu à la pédale (plugin SimHub de ChrGri). Les réglages "
                                   "ci-dessus restent valables.")))
            il.addWidget(c)
            self.cards.append((c, rows))
        c, l = card(T("Profils"))
        hb = QHBoxLayout()
        b1 = QPushButton(T("Exporter…"))
        b1.clicked.connect(self.export)
        b2 = QPushButton(T("Importer…"))
        b2.clicked.connect(self.import_)
        hb.addWidget(b1)
        hb.addWidget(b2)
        hb.addStretch()
        l.addLayout(hb)
        l.addWidget(hint(T("Fichier JSON avec tous les champs de la configuration de la pédale.")))
        il.addWidget(c)
        il.addStretch()
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setWidget(inner)
        sc.setMinimumWidth(430)
        body.addWidget(sc, 1)

        # ------------------------------------------- courbe + direct
        right = QVBoxLayout()
        right.setSpacing(12)
        c, l = card(T("Courbe de force"))
        l.addWidget(hint(T("Force demandée selon la course. Le point bleu montre la pédale en direct.")))
        self.curve = CurveEditor(T("Courbe de force"), PP.CURVE_TRAVEL, PP.CURVE_FORCE, "quantityOfControl_u8",
                                 T("Course"), T("Force"))
        self.curve.edited.connect(self._dirty)
        l.addWidget(self.curve, 1)
        right.addWidget(c, 3)
        self.joy_card, l = card(T("Courbe de l'axe de jeu"))
        l.addWidget(hint(T("Valeur envoyée au jeu selon la force (ou la course). Linéaire par défaut.")))
        self.joy = CurveEditor(T("Axe de jeu"), PP.JOY_ORIG, PP.JOY_MAP, "numOfJoystickMapControl_u8",
                               T("Entrée"), T("Sortie"))
        self.joy.edited.connect(self._dirty)
        l.addWidget(self.joy, 1)
        right.addWidget(self.joy_card, 2)
        c, l = card(T("En direct"))
        g = QGridLayout()
        self.bars = {}
        for i, (k, lab) in enumerate((("pos", T("Course")), ("force", T("Force")), ("joy", T("Axe envoyé au jeu")))):
            g.addWidget(QLabel(lab), i, 0)
            bar = AxisBar(color=(C["accent"], C["blue"], C["ok"])[i])
            bar.setMinimumWidth(160)
            g.addWidget(bar, i, 1)
            v = QLabel("—")
            v.setObjectName("midValue")
            v.setMinimumWidth(130)
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            g.addWidget(v, i, 2)
            self.bars[k] = (bar, v)
        g.setColumnStretch(1, 1)
        l.addLayout(g)
        self.s_err = QLabel("")
        self.s_err.setWordWrap(True)
        l.addWidget(self.s_err)
        self.log = QPlainTextEdit()
        self.log.setObjectName("console")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(300)
        self.log.setMaximumHeight(90)
        self.log.setToolTip(T("Messages texte envoyés par le firmware de la pédale."))
        l.addWidget(self.log)
        right.insertWidget(0, c, 0)          # « En direct » en haut : visible pendant qu'on règle la courbe
        body.addLayout(right, 1)
        root.addLayout(body, 1)

        self.m.changed.connect(self._refresh_list)
        self.m.config_read.connect(self._on_config)
        self.m.states.connect(self._on_states)
        self.m.text.connect(self._on_text)
        self._show_adv(False)
        self._refresh_list()
        self._enable(False)
        t = QTimer(self)
        t.timeout.connect(self._status)
        t.start(500)

    # ------------------------------------------------------------ sélection
    def _refresh_list(self):
        cur = self.port
        self.sel.blockSignals(True)
        self.sel.clear()
        for p in self.m.pedals():
            self.sel.addItem(p.name, p.port)
        self.sel.blockSignals(False)
        if self.sel.count() == 0:
            self.port = None
            self._enable(False)
            self.status.setText(T("Aucune pédale détectée. Branche la pédale par son port USB « UART » (puce "
                                  "CH343/CP210x) et ferme SimHub."))
            return
        i = self.sel.findData(cur)
        self.sel.setCurrentIndex(i if i >= 0 else 0)
        self._select()

    def _select(self, *_):
        port = self.sel.currentData()
        if port == self.port and self.cfg is not None:
            return
        self.port = port
        self.cfg = None
        self.hist.clear()
        info = self.m.info(port)
        if info and info.config:
            self._on_config(port, info.config)
        else:
            self._enable(False)
            if port:
                self.m.request_config(port)

    def _enable(self, on):
        for w in (self.b_apply, self.b_save, self.b_read, self.b_beep):
            w.setEnabled(on)
        for r in self.rows.values():
            r.setEnabled(on)
        self.curve.setEnabled(on)
        self.joy.setEnabled(on)

    def _show_adv(self, on):
        for c, rows in self.cards:
            vis = False
            for r in rows:
                v = on or not r.f.adv
                r.setVisible(v)
                vis |= v
            c.setVisible(vis)
        self.joy_card.setVisible(on)
        self.log.setVisible(on)

    # ------------------------------------------------------------ données
    def _on_config(self, port, cfg):
        info = self.m.info(port)
        if port != self.port:
            return
        self.cfg = dict(cfg)
        for n, r in self.rows.items():
            r.set_device(cfg[n])
        self.curve.set_cfg(cfg)
        self.joy.set_cfg(cfg)
        self._enable(True)
        self._dirty()
        self.status.setText(self._status_text(info))
        self._refresh_names()

    def _refresh_names(self):
        for i in range(self.sel.count()):
            p = self.m.info(self.sel.itemData(i))
            if p:
                self.sel.setItemText(i, p.name)

    def _status_text(self, info):
        if not info:
            return ""
        parts = [PP.PEDAL_NAMES.get(info.tag, "?") if info.tag is not None else "?",
                 T("firmware {v}").format(v=info.fw or "?"), f"{info.rate:.0f} " + T("états/s")]
        st = info.state or {}
        if st:
            parts.append(PP.SERVO_STATUS.get(st.get("servoStatus_u8"), "?"))
        if info.incompatible:
            return T("Firmware incompatible (structure v{v}, attendu v{w}) : flashe le firmware fourni dans "
                     "Pédales › Firmware.").format(v=info.version, w=PP.VERSION)
        return "  ·  ".join(parts)

    def _status(self):
        info = self.m.info(self.port) if self.port else None
        if info:
            self.status.setText(self._status_text(info))
            if info.incompatible:
                self._enable(False)

    def _on_states(self, batch):
        if not self.isVisible():
            return
        last = None
        for port, t, st in batch:
            if port == self.port:
                last = st
        if last is None:
            return
        cfg = self.cfg
        pos, frc, joy = _pct(last["pedalPosition_u16"]), _pct(last["pedalForce_u16"]), _pct(last["joystickOutput_u16"])
        self.bars["pos"][0].set(pos / 100)
        self.bars["pos"][1].setText(f"{pos:5.1f} %")
        self.bars["force"][0].set(frc / 100)
        if cfg:
            kg = cfg["preloadForce_fl32"] + frc / 100 * (cfg["maxForce_fl32"] - cfg["preloadForce_fl32"])
            self.bars["force"][1].setText(f"{kg:5.1f} kg")
        else:
            self.bars["force"][1].setText(f"{frc:5.1f} %")
        self.bars["joy"][0].set(joy / 100)
        self.bars["joy"][1].setText(f"{joy:5.1f} %")
        self.curve.set_live(pos, frc)
        e = last.get("errorCode_u8", 0)
        if e:
            self.s_err.setText(T("Erreur {c} : {d}").format(c=e, d=PP.ERROR_CODES.get(e, T("code inconnu"))))
            self.s_err.setStyleSheet(f"color: {C['bad']};")
        else:
            self.s_err.setText(T("Aucune erreur."))
            self.s_err.setStyleSheet(f"color: {C['ok']};")

    def _on_text(self, port, line):
        if port == self.port:
            self.log.appendPlainText(line)

    # ------------------------------------------------------------ modifications
    def _effective(self):
        if self.cfg is None:
            return None
        c = dict(self.cfg)
        for n, r in self.rows.items():
            c[n] = r.value()
        c.update(self.curve.values())
        c.update(self.joy.values())
        return c

    def _dirty(self):
        n = sum(r.modified() for r in self.rows.values()) + int(self.curve.modified()) + int(self.joy.modified())
        self.b_apply.setText(T("Appliquer ({n})").format(n=n) if n else T("Appliquer"))

    def send(self, store):
        c = self._effective()
        if c is None:
            return
        probs = [p for p in (self.curve.problems(), self.joy.problems()) if p]
        if probs:
            QMessageBox.warning(self, T("Pédale"), "\n".join(probs))
            return
        if store and QMessageBox.question(self, T("Enregistrer dans la pédale"),
                                          T("Mémoriser ces réglages dans la pédale ? Ils remplaceront ceux enregistrés.")) \
                != QMessageBox.Yes:
            return
        err = self.m.send_config(self.port, c, store)
        if err:
            QMessageBox.warning(self, T("Pédale"), T("Réglages refusés (la pédale les ignorerait) : {e}").format(e=err))

    def test_abs(self):
        if not self.port:
            return
        self.m.action(self.port, T("test ABS"), triggerAbs_u8=1)
        QTimer.singleShot(1000, lambda: self.m.action(self.port, "", triggerAbs_u8=0))

    def export(self):
        c = self._effective()
        if not c:
            return
        fn, _ = QFileDialog.getSaveFileName(self, T("Exporter"), time.strftime("pedale_%Y-%m-%d_%H-%M.json"),
                                            "JSON (*.json)")
        if fn:
            with open(fn, "w", encoding="utf-8") as fh:
                json.dump({"simforge_pedal_config": PP.VERSION, "config": c}, fh, indent=1)

    def import_(self):
        if self.cfg is None:
            return
        fn, _ = QFileDialog.getOpenFileName(self, T("Importer"), "", "JSON (*.json)")
        if not fn:
            return
        try:
            with open(fn, encoding="utf-8") as fh:
                d = json.load(fh)
            c = d.get("config", d)
            missing = [n for n in PP.CONFIG_NAMES if n not in c]
            if missing:
                raise ValueError(T("{n} champs manquants").format(n=len(missing)))
        except Exception as e:
            QMessageBox.warning(self, T("Importer"), T("Fichier illisible : {e}").format(e=e))
            return
        for n, r in self.rows.items():
            r.set(c[n])
        tmp = dict(self.cfg)
        tmp.update({k: c[k] for k in PP.CURVE_FORCE + PP.CURVE_TRAVEL + PP.JOY_ORIG + PP.JOY_MAP +
                    ["quantityOfControl_u8", "numOfJoystickMapControl_u8"]})
        dev_c, dev_j = self.curve.device, self.joy.device
        self.curve.set_cfg(tmp)
        self.joy.set_cfg(tmp)
        self.curve.device, self.joy.device = dev_c, dev_j
        self._dirty()
