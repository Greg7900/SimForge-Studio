"""Page Pédales › Réglages de chaque pédale active ChrGri, organisée comme le plugin SimHub de ChrGri :
onglets des pédales, colonne d'infos à gauche, onglets de réglage à droite (avec le schéma de cinématique)."""
from __future__ import annotations

import json
import math
import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer, Signal, QPointF, QRectF, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
                               QCheckBox, QDoubleSpinBox, QSpinBox, QScrollArea, QMessageBox, QFileDialog,
                               QPlainTextEdit, QTabBar)

from . import ped_protocol as PP
from .ped_autotune import AutoTune
from .i18n import T
from .theme import C
from .widgets import card, hint, repolish, AxisBar, TabPages, StatRow, grid, save_json



def _pct(v):
    return (v or 0) / 65535 * 100


class Plot(pg.PlotWidget):
    """Graphique fixe dont on déplace les points de la courbe à la souris (comme le plugin SimHub).
    La molette fait défiler la page au lieu d'être avalée par le graphique."""

    def __init__(self, editor):
        super().__init__()
        self.editor = editor            # CurveEditor : points() et drag_point(i, x, y)
        self.drag = None                # n° du point en cours de déplacement
        self.setMouseTracking(True)

    def _view(self, pos):
        return self.plotItem.vb.mapSceneToView(self.mapToScene(pos))

    def _near(self, pos):
        vb = self.plotItem.vb
        for i, (x, y) in enumerate(self.editor.points()):
            q = self.mapFromScene(vb.mapViewToScene(QPointF(x, y)))
            if abs(q.x() - pos.x()) <= 9 and abs(q.y() - pos.y()) <= 9:
                return i
        return None

    def mousePressEvent(self, ev):
        pos = ev.position().toPoint()
        if ev.button() == Qt.LeftButton and self.editor.isEnabled() and self._near(pos) is not None:
            self.drag = self._near(pos)
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        pos = ev.position().toPoint()
        if self.drag is not None:
            v = self._view(pos)
            self.editor.drag_point(self.drag, v.x(), v.y())
            return
        near = self.editor.isEnabled() and self._near(pos) is not None
        self.viewport().setCursor(Qt.SizeAllCursor if near else Qt.ArrowCursor)
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if self.drag is not None:
            self.drag = None
            return
        super().mouseReleaseEvent(ev)

    def wheelEvent(self, ev):
        ev.ignore()


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
        self.plot = Plot(self)
        self.plot.setMinimumHeight(170)
        grid(self.plot)
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

    def points(self):
        n = self.n.value()
        return [(self.sx[i].value(), self.sy[i].value()) for i in range(n)]

    def drag_point(self, i, x, y):
        """Point déplacé à la souris : le premier et le dernier restent à 0 % et 100 % de l'axe horizontal,
        les autres restent entre leurs voisins."""
        n = self.n.value()
        self._block = True
        if 0 < i < n - 1:
            self.sx[i].setValue(max(self.sx[i - 1].value() + 1, min(self.sx[i + 1].value() - 1, round(x))))
        self.sy[i].setValue(max(0, min(100, round(y))))
        self._block = False
        self._val()

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


class KinematicsView(QWidget):
    """Schéma de la cinématique de la pédale, mêmes lettres que le plugin SimHub de ChrGri.

    O pivot bas de la pédale · A début de course du chariot · B articulation du capteur sur le chariot
    C articulation du capteur sur la pédale · D bout de la pédale.
    Cotes : a = B→C, b = O→C, c horizontale = O→A, c verticale = hauteur de B, d = C→D ; la course part de A.
    Un clic sur une cote ouvre un champ de saisie à cet endroit (signal edited).
    """
    edited = Signal(str, int)               # (nom du champ de configuration, nouvelle valeur en mm)

    # cote affichée → (champ de configuration, couleur)
    DIMS = {"a": ("lengthPedalA_i16", "blue"), "b": ("lengthPedalB_i16", "accent"),
            "c horiz.": ("lengthPedalCHorizontal_i16", "dim"), "c vert.": ("lengthPedalCVertical_i16", "dim"),
            "d": ("lengthPedalD_i16", "accent"), "course": ("lengthPedalTravel_i16", "bad")}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = None
        self.modified = set()       # champs modifiés et pas encore envoyés (affichés en ambre)
        self.live = None            # position de la pédale 0..1 (dans la plage début/fin de course)
        self.hits = {}              # champ → zone cliquable de sa valeur
        self.setMinimumHeight(300)
        self.setMouseTracking(True)
        self.editor = QSpinBox(self)
        self.editor.setSuffix(" mm")
        self.editor.setAlignment(Qt.AlignCenter)
        # NoButtons + la feuille de style masquait le chiffre : flèches gardées mais réduites à 0 px (comme la courbe)
        self.editor.setStyleSheet("QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }")
        self.editor.hide()
        self.editor.editingFinished.connect(self._commit)
        for w in (self.editor, self.editor.lineEdit()):      # Échap peut arriver sur l'un ou l'autre
            w.installEventFilter(self)
        self._editing = None

    def set_cfg(self, cfg, modified=()):
        self.cfg = cfg
        self.modified = set(modified)
        self.update()

    def set_live(self, r01):
        self.live = r01
        self.update()

    # ------------------------------------------------------------ saisie
    def mousePressEvent(self, ev):
        for name, r in self.hits.items():
            if r.contains(ev.position()):
                self._open(name, r)
                return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        over = any(r.contains(ev.position()) for r in self.hits.values())
        self.setCursor(Qt.PointingHandCursor if over else Qt.ArrowCursor)

    def _open(self, name, r):
        f = PP.PBY[name]
        self._editing = name
        self.editor.setRange(int(f.lo), int(f.hi))
        self.editor.setValue(int(self.cfg[name]))
        self._place(r)
        self.editor.setToolTip(f.label)
        self.editor.show()
        self.editor.setFocus()
        self.editor.selectAll()

    def _place(self, r):
        h = max(30, self.editor.sizeHint().height())
        self.editor.setGeometry(int(r.x()) - 4, int(r.center().y() - h / 2), max(110, int(r.width()) + 24), h)

    def _commit(self):
        name, self._editing = self._editing, None
        self.editor.hide()
        if name is not None and self.cfg is not None and self.editor.value() != self.cfg[name]:
            self.edited.emit(name, self.editor.value())

    def eventFilter(self, obj, ev):
        if obj in (self.editor, self.editor.lineEdit()) and ev.type() == QEvent.KeyPress \
                and ev.key() == Qt.Key_Escape:
            self._editing = None            # Échap : on referme sans rien changer
            self.editor.hide()
            return True
        return super().eventFilter(obj, ev)

    # ------------------------------------------------------------ géométrie
    def _angle(self, sled):
        """Angle de la pédale (rad) pour une position du chariot (mm), comme le plugin."""
        c = self.cfg
        b, a = c["lengthPedalB_i16"], c["lengthPedalA_i16"]
        ch, cv = c["lengthPedalCHorizontal_i16"] + sled, c["lengthPedalCVertical_i16"]
        ob = math.hypot(ch, cv)
        if not (a and b and ob):
            return None
        k = (b * b + ob * ob - a * a) / (2 * b * ob)
        return math.acos(max(-1.0, min(1.0, k))) + math.atan2(cv, ch)

    def angles(self):
        """(angle actuel, angle au début, angle à la fin) en degrés, ou None."""
        if not self.cfg:
            return None
        c = self.cfg
        tr = c["lengthPedalTravel_i16"]
        start, end = c["pedalStartPosition_u8"] / 100, c["pedalEndPosition_u8"] / 100
        live = self.live if self.live is not None else 0.0
        vals = [self._angle(tr * (start + live * (end - start))), self._angle(tr * start), self._angle(tr * end)]
        return None if None in vals else [math.degrees(v) for v in vals]

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(C["bg"]))
        self.hits = {}
        if not self.cfg:
            p.setPen(QColor(C["dim"]))
            p.drawText(self.rect(), Qt.AlignCenter, T("Pas de configuration lue"))
            return
        c = self.cfg
        b, d = c["lengthPedalB_i16"], c["lengthPedalD_i16"]
        ch, cv, tr = c["lengthPedalCHorizontal_i16"], c["lengthPedalCVertical_i16"], c["lengthPedalTravel_i16"]
        start, end = c["pedalStartPosition_u8"] / 100, c["pedalEndPosition_u8"] / 100
        live = self.live if self.live is not None else 0.0
        sled = tr * (start + live * (end - start))
        th = self._angle(sled)
        if th is None:
            th = math.pi / 2                # cotes impossibles : on dessine quand même pour pouvoir les corriger
            p.setPen(QColor(C["bad"]))
            p.drawText(self.rect().adjusted(0, 6, -8, 0), Qt.AlignRight | Qt.AlignTop,
                       T("Cotes impossibles : la pédale ne peut pas se monter ainsi"))
        # points en mm (y vers le haut)
        O = (0.0, 0.0)
        A = (float(ch), 0.0)
        B = (ch + sled, float(cv))
        Cp = (b * math.cos(th), b * math.sin(th))
        D = ((b + d) * math.cos(th), (b + d) * math.sin(th))
        pts = [O, A, B, Cp, D, (ch + tr, 0.0)]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        mx, my = 40, 36
        sc = min((self.width() - 2 * mx - 110) / max(1.0, x1 - x0), (self.height() - 2 * my) / max(1.0, y1 - y0))

        def P(q):
            return QPointF(mx + (q[0] - x0) * sc, self.height() - my - (q[1] - y0) * sc)

        # sol / rail et course du chariot
        p.setPen(QPen(QColor(C["line"]), 2))
        p.drawLine(P((x0 - 10, 0)), P((x1 + 10, 0)))
        p.setPen(QPen(QColor(C["bad"]), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(P((ch + tr * start, 0)), P((ch + tr * end, 0)))
        p.setPen(QPen(QColor(C["bad"]).darker(170), 2, Qt.DashLine))
        p.drawLine(P(A), P((ch + tr, 0)))
        # segments
        seg = {"c horiz.": (O, A), "c vert.": ((B[0], 0.0), B), "a": (B, Cp), "b": (O, Cp), "d": (Cp, D)}
        for name, (q1, q2) in seg.items():
            col = C[self.DIMS[name][1]]
            solid = name in ("a", "b", "d")
            p.setPen(QPen(QColor(col), 3 if solid else 1.5, Qt.SolidLine if solid else Qt.DashLine, Qt.RoundCap))
            p.drawLine(P(q1), P(q2))
        # articulations
        p.setFont(QFont(p.font().family(), 10, QFont.Bold))
        off = {"O": (-16, 4), "A": (-4, 18), "B": (8, 4), "C": (-18, -6), "D": (-18, -6)}
        for name, q in (("O", O), ("A", A), ("B", B), ("C", Cp), ("D", D)):
            pt = P(q)
            p.setPen(QPen(QColor(C["text"]), 1.5))
            p.setBrush(QColor(C["panel"]))
            p.drawEllipse(pt, 5, 5)
            p.drawText(pt + QPointF(*off[name]), name)
        # valeurs cliquables
        anchors = {name: (P(q1) + P(q2)) / 2 + QPointF(8, -12) for name, (q1, q2) in seg.items()}
        anchors["c horiz."] = (P(O) + P(A)) / 2 + QPointF(-40, -24)
        anchors["course"] = P((ch + tr / 2, 0)) + QPointF(-40, 8)
        font = QFont(p.font().family(), 9)
        p.setFont(font)
        fm = p.fontMetrics()
        for name, at in anchors.items():
            field, colkey = self.DIMS[name]
            txt = f"{T('course') if name == 'course' else name} = {c[field]} mm"
            r = QRectF(at.x(), at.y(), fm.horizontalAdvance(txt) + 14, fm.height() + 6)
            mod = field in self.modified
            p.setPen(QPen(QColor(C["accent"] if mod else C["line"]), 1))
            p.setBrush(QColor(C["panel2"]))
            p.drawRoundedRect(r, 4, 4)
            p.setPen(QColor(C["accent"] if mod else C[colkey] if colkey != "dim" else C["text"]))
            p.drawText(r, Qt.AlignCenter, txt)
            self.hits[field] = r
        if self._editing in self.hits:            # le schéma a bougé pendant la saisie : le champ suit sa cote
            self._place(self.hits[self._editing])


class PedalsTab(QWidget):
    """Organisation reprise du plugin SimHub de ChrGri : onglets des pédales en haut, colonne de gauche (infos,
    direct, actions, profil) et, à droite, trois groupes d'onglets (courbe / cinématique / axe de jeu,
    réglages généraux, effets)."""

    ROLES = (0, 1, 2)       # Embrayage, Frein, Accélérateur : toujours affichés, comme dans le plugin

    def __init__(self, mgr, parent=None):
        super().__init__(parent)
        self.m = mgr
        self.port = None
        self.cfg = None                 # dernière config lue (brute, complète)
        self.rows: dict[str, PRow] = {}
        self._discard = False
        self._extra = {}                    # réglages importés sans ligne à l'écran (effets, axe frein d'orteil…)
        self.hist = deque(maxlen=1500)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 8)
        root.setSpacing(8)

        # ------------------------------------------- onglets des pédales
        self.sel = QTabBar()
        self.sel.setExpanding(False)
        self.sel.setDrawBase(False)
        self.sel.setStyleSheet("QTabBar::tab { font-size: 12pt; padding: 10px 26px; }")
        self.sel.currentChanged.connect(self._select)
        root.addWidget(self.sel)

        body = QHBoxLayout()
        body.setSpacing(12)

        # ------------------------------------------- colonne de gauche
        left = QWidget()
        left.setFixedWidth(270)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)

        c, l = card(T("Pédale"))
        self.status = QLabel(T("Aucune pédale détectée"))
        self.status.setObjectName("hint")
        self.status.setWordWrap(True)
        l.addWidget(self.status)
        self.s_err = QLabel("")
        self.s_err.setWordWrap(True)
        l.addWidget(self.s_err)
        ll.addWidget(c)

        c, l = card(T("En direct"))
        g = QGridLayout()
        g.setHorizontalSpacing(8)
        self.bars = {}
        for i, (k, lab) in enumerate((("pos", T("Course")), ("force", T("Force")), ("joy", T("Axe envoyé au jeu")))):
            g.addWidget(QLabel(lab), 2 * i, 0, 1, 2)
            bar = AxisBar(color=(C["accent"], C["blue"], C["ok"])[i])
            g.addWidget(bar, 2 * i + 1, 0)
            v = QLabel("—")
            v.setObjectName("midValue")
            v.setMinimumWidth(90)
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            g.addWidget(v, 2 * i + 1, 1)
            self.bars[k] = (bar, v)
        g.setColumnStretch(0, 1)
        l.addLayout(g)
        ll.addWidget(c)

        c, l = card(T("Actions"))
        g = QGridLayout()
        g.setSpacing(6)
        # la carte V6 n'a ni buzzer ni LED pilotée (USING_BUZZER / USING_LED absents de son firmware) : le bip
        # d'identification (action 11) n'y fait rien ; une courte vibration ABS, elle, marche par le port série
        self.b_ident = QPushButton(T("Identifier"))
        self.b_ident.setToolTip(T("Fait vibrer la pédale (et ronronner son moteur) une demi-seconde pour la "
                                  "reconnaître, pied levé. Vibration fixe : tes réglages ABS ne sont pas utilisés et "
                                  "restent tels quels. Les modifications en attente ne sont pas envoyées."))
        self.b_ident.clicked.connect(self.identify)
        self.b_read = QPushButton(T("Relire"))
        self.b_read.clicked.connect(self._reread)
        self.b_exp = QPushButton(T("Exporter…"))
        self.b_exp.clicked.connect(self.export)
        self.b_imp = QPushButton(T("Importer…"))
        self.b_imp.setToolTip(T("Fichier JSON avec tous les champs de la configuration de la pédale."))
        self.b_imp.clicked.connect(self.import_)
        # restent utilisables même sans configuration lue : c'est justement quand la pédale est bloquée qu'on en a besoin
        self.b_wake = QPushButton(T("Réveiller"))
        self.b_wake.setToolTip(T("Sort la pédale de l'attente du logiciel au démarrage (LED bleue, réglage « Au "
                                 "démarrage : attend le logiciel »). Après la « Mise en veille du servo » (LED rouge), "
                                 "seul un appui franc sur la pédale la réveille."))
        self.b_wake.clicked.connect(lambda: self.m.action(self.port, T("réveil de la pédale"),
                                                         systemAction_u8=PP.ACT_WAKEUP))
        self.b_restart = QPushButton(T("Redémarrer"))
        self.b_restart.setToolTip(T("Redémarre la pédale (comme débrancher/rebrancher son alimentation USB)."))
        self.b_restart.clicked.connect(self.restart)
        self.b_alarm = QPushButton(T("Alarmes servo"))
        self.b_alarm.setToolTip(T("Le servo peut se mettre en alarme (surtension…) et bloquer la pédale sans que la "
                                  "carte le voie : LED verte, aucune erreur. Ce bouton écrit l'historique des alarmes "
                                  "dans les messages puis les efface, ce qui relance le servo sans redémarrer. La "
                                  "pédale se fige 1 s ; les modifications en attente ne sont pas envoyées."))
        self.b_alarm.clicked.connect(self.clear_alarms)
        self.b_info = QPushButton(T("Infos firmware"))
        self.b_info.setToolTip(T("Demande à la pédale d'écrire ses informations dans les messages."))
        self.b_info.clicked.connect(lambda: self.m.action(self.port, T("infos firmware"),
                                                         systemAction_u8=PP.ACT_PRINT_INFO))
        for i, b in enumerate((self.b_ident, self.b_read, self.b_exp, self.b_imp, self.b_wake, self.b_restart,
                               self.b_alarm, self.b_info)):
            g.addWidget(b, i // 2, i % 2)
        l.addLayout(g)
        ll.addWidget(c)

        c, l = card(T("Messages"))
        self.log = QPlainTextEdit()
        self.log.setObjectName("console")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(300)
        self.log.setToolTip(T("Messages texte envoyés par le firmware de la pédale."))
        l.addWidget(self.log)
        ll.addWidget(c, 1)

        self.b_apply = QPushButton(T("Appliquer"))
        self.b_apply.setToolTip(T("Envoie les réglages à la pédale sans les mémoriser (perdus au redémarrage)."))
        self.b_apply.clicked.connect(lambda: self.send(False))
        ll.addWidget(self.b_apply)
        self.b_save = QPushButton(T("Enregistrer dans la pédale"))
        self.b_save.setObjectName("primary")
        self.b_save.clicked.connect(lambda: self.send(True))
        ll.addWidget(self.b_save)
        body.addWidget(left)

        # ------------------------------------------- onglets de réglage
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 6, 0)
        il.setSpacing(12)
        self.cards = []

        self.curve = CurveEditor(T("Courbe de force"), PP.CURVE_TRAVEL, PP.CURVE_FORCE, "quantityOfControl_u8",
                                 T("Course"), T("Force"))
        self.curve.edited.connect(self._dirty)
        self.joy = CurveEditor(T("Axe de jeu"), PP.JOY_ORIG, PP.JOY_MAP, "numOfJoystickMapControl_u8",
                               T("Entrée"), T("Sortie"))
        self.joy.edited.connect(self._dirty)
        self.kin = KinematicsView()
        self.kin_info = hint("")

        pages = self._tab_group(il, PP.TABS_CURVE)
        pages[PP.G_CURVE].addWidget(hint(T("Force demandée selon la course. Fais glisser les points orange pour régler la courbe ; "
                                           "le point bleu montre la pédale en direct.")))
        pages[PP.G_CURVE].addWidget(self.curve, 1)
        # les cotes se saisissent sur le schéma : leurs lignes restent comme support des valeurs, cachées
        for f in PP.PFIELDS:
            if f.group == PP.G_KIN:
                self.rows[f.name].hide()
        self.kin.edited.connect(lambda name, v: self.rows[name].ed.setValue(v))
        pages[PP.G_KIN].insertWidget(0, hint(T("Clique sur une cote du schéma pour la modifier (Entrée pour valider, "
                                               "Échap pour annuler). Les cotes modifiées sont en orange.")))
        pages[PP.G_KIN].insertWidget(1, self.kin, 1)
        pages[PP.G_KIN].insertWidget(2, self.kin_info)
        pages[PP.G_KIN].insertWidget(3, hint(T(
            "O : pivot bas de la pédale · A : début de la course du chariot · B : articulation du capteur de force "
            "sur le chariot · C : articulation du capteur sur la pédale · D : bout de la pédale (appui du pied). "
            "Le trait rouge est la course utilisée (entre début et fin de course).")))
        pages[PP.G_JOY].addWidget(hint(T("Valeur envoyée au jeu selon la force (ou la course). Linéaire par défaut. "
                                         "Fais glisser les points pour la régler.")))
        pages[PP.G_JOY].addWidget(self.joy, 1)

        pages = self._tab_group(il, PP.TABS_GENERAL)
        self._build_diag(pages[PP.G_DIAG])
        self.autotune = AutoTune(self)
        pages[PP.G_AUTO].addWidget(self.autotune)

        pages = self._tab_group(il, PP.TABS_FX, T("Effets"))
        hb = QHBoxLayout()
        self.b_abs = QPushButton(T("Tester l'ABS (1 s)"))
        self.b_abs.setToolTip(T("Déclenche l'effet ABS pendant 1 seconde, sans jeu : appuie sur la pédale."))
        self.b_abs.clicked.connect(self.test_abs)
        hb.addWidget(self.b_abs)
        hb.addStretch()
        pages[PP.G_ABS].addLayout(hb)
        self.fx_card.layout().addWidget(hint(T(
            "En jeu, les effets (ABS, régime, patinage…) ne marchent que si un logiciel envoie la télémétrie du jeu "
            "à la pédale (plugin SimHub de ChrGri). Les réglages ci-dessus restent valables.")))
        for pl in self._pages:
            if pl not in self._curve_pages:      # courbes et schéma prennent toute la hauteur
                pl.addStretch(1)
        il.addStretch()

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setWidget(inner)
        sc.setMinimumWidth(520)
        body.addWidget(sc, 1)
        root.addLayout(body, 1)

        self.m.changed.connect(self._refresh_list)
        self.m.config_read.connect(self._on_config)
        self.m.states.connect(self._on_states)
        self.m.text.connect(self._on_text)
        self._refresh_list()
        self._enable(False)
        t = QTimer(self)
        t.timeout.connect(self._status)
        t.start(500)

    # ------------------------------------------------------------ diagnostic du servo
    def _build_diag(self, pl):
        pl.addWidget(hint(T(
            "État détaillé envoyé par la pédale : sert à comprendre un servo qui se bloque. Si la tension monte à "
            "chaque relâcher jusqu'au blocage, l'énergie de freinage n'est pas évacuée (onglet Général, « Énergie "
            "de freinage du servo »).")))
        self.diag_on = QCheckBox(T("Recevoir l'état détaillé du servo"))
        self.diag_on.setToolTip(T("Applique (sans mémoriser) le drapeau de débogage 64 + 4 de la pédale. Les "
                                  "modifications en attente ne sont pas envoyées."))
        self.diag_on.toggled.connect(self._diag_toggle)
        pl.addWidget(self.diag_on)
        g = QGridLayout()
        g.setHorizontalSpacing(16)
        self.diag = {}
        items = (("v", T("Tension du servo"), "V"), ("vmax", T("Tension la plus haute"), "V"),
                 ("i", T("Courant du servo"), "%"), ("err", T("Écart de position (consigne − réelle)"), T("pas")),
                 ("rpm", T("Vitesse du servo"), T("tr/min")), ("br", T("Résistance de freinage"), ""))
        for k, (key, lab, unit) in enumerate(items):
            r = StatRow(lab, unit)
            g.addWidget(r, k // 2, k % 2)
            self.diag[key] = r
        pl.addLayout(g)
        hb = QHBoxLayout()
        b = QPushButton(T("Remettre le maxi à zéro"))
        b.clicked.connect(self._diag_reset)
        hb.addWidget(b)
        hb.addStretch()
        pl.addLayout(hb)
        self.diag_plot = pg.PlotWidget()
        self.diag_plot.setMinimumHeight(170)
        self.diag_plot.setMouseEnabled(x=False, y=False)
        self.diag_plot.setMenuEnabled(False)
        grid(self.diag_plot)
        self.diag_plot.setLabel("left", T("Tension"), "V")
        self.diag_plot.setLabel("bottom", T("Temps"), "s")
        for ax in ("left", "bottom"):
            self.diag_plot.getAxis(ax).enableAutoSIPrefix(False)
        self.diag_curve = self.diag_plot.plot(pen=pg.mkPen(C["accent"], width=2))
        pl.addWidget(self.diag_plot)
        self.diag_hist = deque(maxlen=300)          # 15 s à 20 Hz
        self.diag_t0 = time.monotonic()
        t = QTimer(self)
        t.timeout.connect(self._diag_update)
        t.start(50)

    def _diag_toggle(self, on):
        if not self.port or self.cfg is None:
            return
        c = dict(self.cfg)                          # configuration de la pédale, sans les modifications en attente
        bits = PP.DBG_EXT_STATE | PP.DBG_EXT_DECIMATED
        c["debugFlags0_u8"] = (c["debugFlags0_u8"] | bits) if on else (c["debugFlags0_u8"] & ~bits & 0xFF)
        err = self.m.send_config(self.port, c, False)
        if err:
            QMessageBox.warning(self, T("Pédale"), T("Réglages refusés (la pédale les ignorerait) : {e}").format(e=err))

    def _diag_reset(self):
        info = self.m.info(self.port) if self.port else None
        if info:
            info.ext_vmax = 0.0
        self.diag_hist.clear()

    def _diag_update(self):
        if not self.diag_plot.isVisible():
            return
        info = self.m.info(self.port) if self.port else None
        ex = info.ext if info else None
        if not ex or not self.diag_on.isChecked():
            for r in self.diag.values():
                r.set("—")
            return
        v = ex["servoVoltage0p1V_i16"] / 10
        self.diag["v"].set(f"{v:.1f}")
        self.diag["vmax"].set(f"{info.ext_vmax:.1f}", C["warn"] if info.ext_vmax > v + 3 else None)
        self.diag["i"].set(f"{ex['servoCurrentPercent_i16']}")
        self.diag["err"].set(f"{ex['servoPositionError_i16']}")
        self.diag["rpm"].set(f"{ex['servoVelocityRpm_i16']}")
        self.diag["br"].set(T("active") if ex["brakeResistorState_b"] else T("inactive"),
                            C["accent"] if ex["brakeResistorState_b"] else None)
        self.diag_hist.append((time.monotonic() - self.diag_t0, v))
        xs = [a for a, _ in self.diag_hist]
        self.diag_curve.setData([x - xs[-1] for x in xs], [b for _, b in self.diag_hist])

    def _tab_group(self, parent_lay, groups, title=""):
        """Carte contenant un onglet par groupe de réglages ; renvoie {groupe: layout de l'onglet}."""
        c, l = card(title)
        tw = TabPages()
        pages = {}
        for g in groups:
            w = QWidget()
            pl = QVBoxLayout(w)
            pl.setContentsMargins(4, 10, 4, 4)
            pl.setSpacing(2)
            for f in PP.PFIELDS:
                if f.group == g:
                    r = PRow(f)
                    r.edited.connect(self._dirty)
                    self.rows[f.name] = r
                    pl.addWidget(r)
            pages[g] = pl
            tw.addTab(w, g)
        l.addWidget(tw, 1)
        parent_lay.addWidget(c)
        self._pages = getattr(self, "_pages", []) + list(pages.values())
        if groups is PP.TABS_CURVE:
            self._curve_pages = (pages[PP.G_CURVE], pages[PP.G_JOY], pages[PP.G_KIN])
        if groups is PP.TABS_FX:
            self.fx_card = c
        return pages

    # ------------------------------------------------------------ sélection
    def _roles(self):
        return [(p.port, p.tag) for p in self.m.pedals()]

    def _refresh_list(self):
        self._roles_shown = self._roles()
        cur = self.port
        self.sel.blockSignals(True)
        while self.sel.count():
            self.sel.removeTab(0)
        tabs = {r: None for r in self.ROLES}
        extra = []
        for p in self.m.pedals():
            if p.tag in tabs and tabs[p.tag] is None:
                tabs[p.tag] = p
            else:
                extra.append(p)
        for r in self.ROLES:
            p = tabs[r]
            i = self.sel.addTab(PP.PEDAL_NAMES[r].upper())
            self.sel.setTabData(i, p.port if p else None)
            self.sel.setTabEnabled(i, p is not None)
            self.sel.setTabToolTip(i, p.port if p else T("Pédale non branchée"))
        for p in extra:
            i = self.sel.addTab(p.name)
            self.sel.setTabData(i, p.port)
        ports = [self.sel.tabData(i) for i in range(self.sel.count())]
        idx = ports.index(cur) if cur is not None and cur in ports else next((i for i, q in enumerate(ports) if q), -1)
        if idx >= 0:
            self.sel.setCurrentIndex(idx)
        self.sel.blockSignals(False)
        if idx < 0:
            self.port = None
            self.cfg = None
            self._enable(False)
            self.kin.set_cfg(None)
            self.status.setText(T("Aucune pédale détectée. Branche la pédale par son port USB « UART » (puce "
                                  "CH343/CP210x), ou par son port USB natif avec le firmware « un câble », et "
                                  "ferme SimHub."))
            return
        self._select()

    def _select(self, *_):
        port = self.sel.tabData(self.sel.currentIndex()) if self.sel.currentIndex() >= 0 else None
        if port is None or (port == self.port and self.cfg is not None):
            return
        self.port = port
        self.cfg = None
        self.hist.clear()
        self.log.clear()
        self._last_line = None
        info = self.m.info(port)
        if info and info.config:
            self._on_config(port, info.config)
        else:
            self._enable(False)
            self.m.request_config(port)

    def _enable(self, on):
        for w in (self.b_apply, self.b_save, self.b_read, self.b_exp, self.b_imp, self.b_abs, self.b_alarm,
                  self.b_ident, self.diag_on):
            w.setEnabled(on)
        for r in self.rows.values():
            r.setEnabled(on)
        self.curve.setEnabled(on)
        self.joy.setEnabled(on)

    # ------------------------------------------------------------ données
    def _on_config(self, port, cfg):
        info = self.m.info(port)
        if port != self.port:
            return
        # relecture automatique (après un envoi, le diagnostic…) : les modifications pas encore envoyées restent ;
        # « Relire » et le changement de pédale repartent de la pédale
        keep = self.cfg is not None and not self._discard
        self._discard = False
        # réglages importés sans ligne à l'écran : en attente tant que la pédale ne les a pas
        self._extra = {k: v for k, v in self._extra.items() if cfg[k] != v} if keep else {}
        self.cfg = dict(cfg)
        for n, r in self.rows.items():
            pending = r.value() if keep and r.modified() else None
            r.set_device(cfg[n])
            if pending is not None:
                r.set(pending)
        for ed in (self.curve, self.joy):
            pending = ed.values() if keep and ed.modified() else None
            ed.set_cfg(cfg)
            if pending is not None:
                dev = ed.device
                tmp = dict(cfg)
                tmp.update(pending)
                ed.set_cfg(tmp)
                ed.device = dev
        self.diag_on.blockSignals(True)
        self.diag_on.setChecked(bool(cfg["debugFlags0_u8"] & PP.DBG_EXT_STATE))
        self.diag_on.blockSignals(False)
        self._enable(True)
        self.autotune.refresh()
        self._dirty()
        self.status.setText(self._status_text(info))

    def _status_text(self, info):
        if not info:
            return ""
        if info.incompatible:
            return T("Firmware incompatible (structure v{v}, attendu v{w}) : flashe le firmware fourni dans "
                     "Pédales › Firmware.").format(v=info.version, w=PP.VERSION)
        parts = [PP.PEDAL_NAMES.get(info.tag, "?") if info.tag is not None else "?", info.port,
                 T("firmware {v}").format(v=info.fw or "?"), f"{info.rate:.0f} " + T("états/s")]
        st = info.state or {}
        if st:
            parts.append(PP.SERVO_STATUS.get(st.get("servoStatus_u8"), "?"))
        return "\n".join(parts)

    def _status(self):
        for b in (self.b_wake, self.b_restart, self.b_info):
            b.setEnabled(self.port is not None)
        # une pédale qui change de rôle (Rôle de la pédale enregistré) doit changer d'onglet
        if self._roles() != self._roles_shown:
            self._refresh_list()
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
        if self.kin.isVisible():
            self.kin.set_live(pos / 100)
            self._kin_text()
        e = last.get("errorCode_u8", 0)
        if e:
            self.s_err.setText(T("Erreur {c} : {d}").format(c=e, d=PP.ERROR_CODES.get(e, T("code inconnu"))))
            self.s_err.setStyleSheet(f"color: {C['bad']};")
        else:
            self.s_err.setText(T("Aucune erreur."))
            self.s_err.setStyleSheet(f"color: {C['ok']};")

    def _on_text(self, port, line):
        if port != self.port:
            return
        # une ligne répétée telle quelle (ex. « [ESPNOW TX] Unhealthy … (EMPTY) » toutes les 5 s sans récepteur
        # sans fil) n'est affichée qu'une fois, pour ne pas noyer les autres messages
        if line == getattr(self, "_last_line", None):
            return
        self._last_line = line
        self.log.appendPlainText(line)
        # explication des messages du servo, une fois par série (l'historique répète souvent la même alarme)
        h = PP.servo_hint(line)
        if h and h != getattr(self, "_last_hint", None):
            self.log.appendPlainText("  → " + h)
        self._last_hint = h

    def _kin_text(self):
        ang = self.kin.angles()
        if ang:
            self.kin_info.setText(T("Angle de la pédale : {c:.0f}°  ·  début de course {s:.0f}°  ·  fin de course "
                                    "{e:.0f}°  ·  débattement {d:.0f}°").format(c=ang[0], s=ang[1], e=ang[2],
                                                                               d=abs(ang[1] - ang[2])))
        else:
            self.kin_info.setText("")

    # ------------------------------------------------------------ modifications
    def _effective(self):
        if self.cfg is None:
            return None
        c = dict(self.cfg)
        for n, r in self.rows.items():
            c[n] = r.value()
        c.update(self.curve.values())
        c.update(self.joy.values())
        c.update(self._extra)
        return c

    def _dirty(self):
        n = (sum(r.modified() for r in self.rows.values()) + int(self.curve.modified()) + int(self.joy.modified())
             + len(self._extra))
        self.b_apply.setText(T("Appliquer ({n})").format(n=n) if n else T("Appliquer"))
        # le schéma suit les cotes en cours de saisie et montre celles pas encore envoyées
        self.kin.set_cfg(self._effective(), [n for n, r in self.rows.items() if r.modified()])
        self._kin_text()

    def send(self, store):
        c = self._effective()
        if c is None:
            return
        probs = [p for p in (self.curve.problems(), self.joy.problems()) if p]
        if probs:
            QMessageBox.warning(self, T("Pédale"), "\n".join(probs))
            return
        role = self.rows["pedalType_u8"]
        if not store and role.modified() and role.device in self.ROLES:
            # le firmware garde le rôle enregistré d'une pédale déjà assignée : seul « Enregistrer » le change
            if QMessageBox.question(self, T("Rôle de la pédale"),
                                    T("Le firmware ne change le rôle d'une pédale déjà assignée qu'en l'enregistrant. "
                                      "Enregistrer tous ces réglages dans la pédale maintenant ?")) != QMessageBox.Yes:
                return
            store = True
        elif store and QMessageBox.question(self, T("Enregistrer dans la pédale"),
                                            T("Mémoriser ces réglages dans la pédale ? Ils remplaceront ceux "
                                              "enregistrés.")) != QMessageBox.Yes:
            return
        err = self.m.send_config(self.port, c, store)
        if err:
            QMessageBox.warning(self, T("Pédale"), T("Réglages refusés (la pédale les ignorerait) : {e}").format(e=err))

    def _reread(self):
        self._discard = True                # « Relire » abandonne les modifications pas encore envoyées
        self.m.request_config(self.port)

    def restart(self):
        if self.port and QMessageBox.question(self, T("Redémarrer"), T("Redémarrer la pédale ? Les réglages non "
                                                                     "enregistrés seront perdus.")) == QMessageBox.Yes:
            self.m.action(self.port, T("redémarrage de la pédale"), systemAction_u8=PP.ACT_RESTART)

    def clear_alarms(self):
        if not self.port or self.cfg is None:
            return
        err = self.m.send_config(self.port, self.cfg, False, clear_alarms=True)   # configuration de la pédale
        if err:
            QMessageBox.warning(self, T("Pédale"), T("Réglages refusés (la pédale les ignorerait) : {e}").format(e=err))

    # Identifier : vibration fixe, indépendante des réglages ABS de la pédale. Le firmware n'a pas d'effet libre :
    # l'ABS est emprunté le temps de la vibration (sur la course, sans seuil de force, donc pied levé), puis la
    # pédale reprend sa configuration
    IDENT_ABS = dict(absAmplitude_u8=30, absFrequency_u8=15, absPattern_u8=0, absForceOrTarvelBit_u8=1,
                     minForceForEffects_u8=0)            # 3 % de la course à 15 Hz
    IDENT_S = 0.6

    def identify(self):
        if not self.port or self.cfg is None:
            return
        port, orig = self.port, dict(self.cfg)      # configuration de la pédale, sans les modifications en attente
        if self.m.send_config(port, dict(orig, **self.IDENT_ABS), False, reread=False):
            return
        self._pulse_abs(port, self.IDENT_S, T("vibration d'identification"),
                        lambda: self.m.send_config(port, orig, False))

    def test_abs(self):
        if not self.port:
            return
        self._pulse_abs(self.port, 1.0, T("test ABS"))

    def _pulse_abs(self, port, seconds, what, then=None):
        """Le firmware arrête l'ABS 100 ms après chaque déclenchement (le plugin le renvoie en continu) : un seul
        envoi ne donnait qu'un dixième de seconde, imperceptible. On le renvoie toutes les 50 ms."""
        t = QTimer(self)
        end = time.monotonic() + seconds

        def tick():
            if time.monotonic() < end:
                self.m.action(port, "", triggerAbs_u8=1)
                return
            t.stop()
            t.deleteLater()
            self.m.action(port, "", triggerAbs_u8=0)
            if then:
                then()
        t.timeout.connect(tick)
        t.start(50)
        self.m.action(port, what, triggerAbs_u8=1)

    def export(self):
        c = self._effective()
        if not c:
            return
        fn, _ = QFileDialog.getSaveFileName(self, T("Exporter"), time.strftime("pedale_%Y-%m-%d_%H-%M.json"),
                                            "JSON (*.json)")
        if fn:
            save_json(self, fn, {"simforge_pedal_config": PP.VERSION, "config": c}, indent=1)

    def import_(self):
        if self.cfg is None:
            return
        fn, _ = QFileDialog.getOpenFileName(self, T("Importer"), "", "JSON (*.json)")
        if not fn:
            return
        try:
            with open(fn, encoding="utf-8") as fh:
                d = json.load(fh)
            c = d.get("config", d) if isinstance(d, dict) else None
            if not isinstance(c, dict):
                raise ValueError(T("format inattendu"))
            missing = [n for n in PP.CONFIG_NAMES if n not in c]
            if missing:
                raise ValueError(T("{n} champs manquants").format(n=len(missing)))
            bad = [n for n in PP.CONFIG_NAMES if not isinstance(c[n], (int, float))]
            if bad:
                raise ValueError(T("valeurs non numériques : {l}").format(l=", ".join(bad[:5])))
        except Exception as e:
            QMessageBox.warning(self, T("Importer"), T("Fichier illisible : {e}").format(e=e))
            return
        for n, r in self.rows.items():
            r.set(c[n])
        # tout le reste du fichier aussi (avant : seuls les réglages affichés, la courbe et l'axe de jeu étaient
        # repris : effets, fenêtres, axe frein d'orteil… restaient ceux de la pédale)
        shown = set(self.rows) | set(PP.CURVE_FORCE + PP.CURVE_TRAVEL + PP.JOY_ORIG + PP.JOY_MAP +
                                     ["quantityOfControl_u8", "numOfJoystickMapControl_u8"])
        self._extra = {n: c[n] for n in PP.CONFIG_NAMES
                       if n not in shown and n != "configHash_u32" and c[n] != self.cfg[n]}
        tmp = dict(self.cfg)
        tmp.update({k: c[k] for k in PP.CURVE_FORCE + PP.CURVE_TRAVEL + PP.JOY_ORIG + PP.JOY_MAP +
                    ["quantityOfControl_u8", "numOfJoystickMapControl_u8"]})
        dev_c, dev_j = self.curve.device, self.joy.device
        self.curve.set_cfg(tmp)
        self.joy.set_cfg(tmp)
        self.curve.device, self.joy.device = dev_c, dev_j
        self._dirty()
