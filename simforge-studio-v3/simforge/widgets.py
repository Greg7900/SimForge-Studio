"""Widgets communs."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QObject, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import (QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QSlider,
                               QSpinBox, QCheckBox, QComboBox, QSizePolicy, QApplication, QAbstractSpinBox,
                               QAbstractSlider, QScrollBar, QTabBar, QAbstractScrollArea)

from .theme import C
from .i18n import T


class WheelGuard(QObject):
    """Filtre global : la molette ne modifie plus un champ (nombre, liste, curseur) ni un onglet simplement survolé,
    elle fait défiler la page. Un champ cliqué (qui a le focus) garde la molette."""

    TYPES = (QAbstractSpinBox, QComboBox, QAbstractSlider, QTabBar)

    def eventFilter(self, obj, ev):
        if ev.type() != QEvent.Wheel or not isinstance(obj, self.TYPES) or isinstance(obj, QScrollBar) \
                or obj.hasFocus():
            return False
        p = obj.parentWidget()
        while p is not None and not isinstance(p, QAbstractScrollArea):
            p = p.parentWidget()
        if p is not None:
            QApplication.sendEvent(p.viewport(), ev)
        return True


def install_wheel_guard(app):
    app._wheel_guard = WheelGuard(app)
    app.installEventFilter(app._wheel_guard)


def card(title: str = "", parent=None):
    f = QFrame(parent)
    f.setObjectName("card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(14, 12, 14, 14)
    lay.setSpacing(8)
    if title:
        t = QLabel(title.upper())
        t.setObjectName("cardTitle")
        lay.addWidget(t)
    return f, lay


def hint(text: str) -> QLabel:
    l = QLabel(text)
    l.setObjectName("hint")
    l.setWordWrap(True)
    return l


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


class Led(QWidget):
    def __init__(self, color=C["dim"], size=10, parent=None):
        super().__init__(parent)
        self._c = QColor(color)
        self._on = True
        self.setFixedSize(size + 4, size + 4)

    def set(self, color: str, on: bool = True):
        self._c, self._on = QColor(color), on
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(self._c) if self._on else QColor(C["line"])
        if self._on:
            g = QColor(c)
            g.setAlpha(60)
            p.setBrush(g)
            p.setPen(Qt.NoPen)
            p.drawEllipse(self.rect())
        p.setBrush(c)
        p.drawEllipse(self.rect().adjusted(2, 2, -2, -2))


class ValueReadout(QWidget):
    """Grosse valeur + unité + libellé."""

    def __init__(self, label: str, unit: str = "", big=True, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        t = QLabel(label.upper())
        t.setObjectName("cardTitle")
        row = QHBoxLayout()
        row.setSpacing(4)
        self.v = QLabel("—")
        self.v.setObjectName("bigValue" if big else "midValue")
        u = QLabel(unit)
        u.setObjectName("unit")
        row.addWidget(self.v)
        row.addWidget(u, 0, Qt.AlignBottom)
        row.addStretch()
        lay.addWidget(t)
        lay.addLayout(row)

    def set(self, text: str, color: str | None = None):
        self.v.setText(text)
        self.v.setStyleSheet(f"color: {color};" if color else "")


class CenterBar(QWidget):
    """Barre à zéro central (-100..+100)."""

    def __init__(self, parent=None, color=C["accent"]):
        super().__init__(parent)
        self.v = 0.0
        self.color = QColor(color)
        self.setMinimumHeight(14)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set(self, v: float):
        self.v = max(-100.0, min(100.0, v))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        r = self.rect().adjusted(0, 3, -1, -3)
        p.fillRect(r, QColor(C["bg"]))
        p.setPen(QColor(C["line"]))
        p.drawRect(r)
        mid = r.center().x()
        w = (r.width() / 2) * (self.v / 100)
        bar = QRectF(mid, r.top() + 1, w, r.height() - 1).normalized()
        p.fillRect(bar, self.color)
        p.setPen(QColor(C["dim"]))
        p.drawLine(mid, r.top() - 2, mid, r.bottom() + 2)


class AxisBar(QWidget):
    """Barre d'axe 0..1 avec curseur."""

    def __init__(self, parent=None, color=C["blue"]):
        super().__init__(parent)
        self.v = 0.5
        self.color = QColor(color)
        self.setMinimumHeight(12)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set(self, v01: float):
        self.v = max(0.0, min(1.0, v01))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        r = self.rect().adjusted(0, 2, -1, -2)
        p.fillRect(r, QColor(C["bg"]))
        p.fillRect(QRectF(r.left(), r.top(), r.width() * self.v, r.height()), self.color.darker(160))
        x = r.left() + r.width() * self.v
        p.setPen(QPen(self.color, 2))
        p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
        p.setPen(QColor(C["line"]))
        p.drawRect(r)


class WheelDial(QWidget):
    """Volant dessiné qui tourne avec l'angle mesuré + arc de course."""

    def __init__(self, parent=None, size=170):
        super().__init__(parent)
        self.angle = 0.0
        self.range = 900
        self.torque = 0.0
        self.setMinimumSize(size, size)

    def set(self, angle: float, motion_range: int, torque: float = 0.0):
        self.angle, self.range, self.torque = angle, motion_range or 900, torque
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height()) - 16
        cx, cy = self.width() / 2, self.height() / 2
        R = s / 2
        # arc de course (fraction de la course utilisée)
        frac = max(-1.0, min(1.0, self.angle / (self.range / 2)))
        rect = QRectF(cx - R, cy - R, 2 * R, 2 * R)
        p.setPen(QPen(QColor(C["line"]), 4))
        p.drawArc(rect, 225 * 16, -270 * 16)
        p.setPen(QPen(QColor(C["accent"]), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 90 * 16, int(-frac * 135 * 16))
        # couple (arc intérieur)
        r2 = R - 9
        p.setPen(QPen(QColor(C["blue"]), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - r2, cy - r2, 2 * r2, 2 * r2), 90 * 16,
                  int(-max(-1, min(1, self.torque / 100)) * 135 * 16))
        # volant
        p.translate(cx, cy)
        p.rotate(self.angle)
        rw = R * 0.70
        p.setPen(QPen(QColor(C["text"]), 7))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), rw, rw)
        p.setPen(QPen(QColor(C["dim"]), 6))
        for a in (90, 210, 330):
            rad = math.radians(a)
            p.drawLine(QPointF(0, 0), QPointF(math.cos(rad) * rw, math.sin(rad) * rw))
        p.setBrush(QColor(C["panel2"]))
        p.setPen(QPen(QColor(C["dim"]), 2))
        p.drawEllipse(QPointF(0, 0), rw * 0.22, rw * 0.22)
        p.setPen(QPen(QColor(C["accent"]), 7, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(0, -rw - 1), QPointF(0, -rw + 9))   # repère haut


# ----------------------------------------------------------------- éditeurs
class SettingRow(QWidget):
    """Ligne de réglage : libellé + (curseur) + spinbox, avec suivi « modifié »."""
    edited = Signal(object)    # nouvelle valeur

    def __init__(self, label: str, lo: int, hi: int, unit: str = "", tip: str = "",
                 slider: bool = True, warn: bool = False, parent=None):
        super().__init__(parent)
        self.device_value = None
        self.title = label
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(10)
        self.lbl = QLabel(("⚠ " if warn else "") + label)
        self.lbl.setMinimumWidth(max(210 if slider else 0, self.lbl.sizeHint().width()))
        if warn:
            self.lbl.setObjectName("warnText")
        if tip:
            self.setToolTip(tip)
        lay.addWidget(self.lbl)
        self.slider = None
        if slider:
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setRange(lo, hi)
            self.slider.setMinimumWidth(140)
            lay.addWidget(self.slider, 1)
        else:
            lay.addStretch(1)
        self.spin = QSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setMinimumWidth(92)
        self.spin.setAlignment(Qt.AlignRight)
        if unit:
            self.spin.setSuffix(f" {unit}")
        self.spin.setKeyboardTracking(False)
        lay.addWidget(self.spin)
        if self.slider:
            self.slider.valueChanged.connect(self._from_slider)
            self.slider.sliderReleased.connect(lambda: self._emit(self.slider.value()))
        self.spin.valueChanged.connect(self._from_spin)

    def set_label_width(self, w):
        """Largeur mini du libellé, jamais inférieure à son texte."""
        self.lbl.setMinimumWidth(max(int(w), self.lbl.sizeHint().width()))

    def _from_slider(self, v):
        self.spin.blockSignals(True)
        self.spin.setValue(v)
        self.spin.blockSignals(False)
        self._mark()
        if not self.slider.isSliderDown():
            self._emit(v)

    def _from_spin(self, v):
        if self.slider:
            self.slider.blockSignals(True)
            self.slider.setValue(v)
            self.slider.blockSignals(False)
        self._emit(v)

    def _emit(self, v):
        self._mark()
        self.edited.emit(v)

    def value(self):
        return self.spin.value()

    def set_device(self, v):
        v = int(v)
        self.device_value = v
        # Ne jamais tronquer une valeur lue dans la carte : on élargit la plage si besoin.
        if v < self.spin.minimum() or v > self.spin.maximum():
            lo, hi = min(v, self.spin.minimum()), max(v, self.spin.maximum())
            for w in (self.spin, self.slider):
                if w:
                    w.blockSignals(True)
                    w.setRange(lo, hi)
                    w.blockSignals(False)
            self.lbl.setToolTip(T("Valeur lue dans la carte ({v}) hors de la plage habituelle : affichée telle quelle.")
                                .format(v=v))
            self.lbl.setText(self.lbl.text().rstrip(" ⚑") + " ⚑")
        self.set_value(v)
        self._mark()

    def set_value(self, v):
        for w in (self.spin, self.slider):
            if w:
                w.blockSignals(True)
                w.setValue(int(v))
                w.blockSignals(False)
        self._mark()

    def modified(self) -> bool:
        return self.device_value is not None and self.value() != self.device_value

    def _mark(self):
        m = "true" if self.modified() else "false"
        for w in (self.spin, self.slider):
            if w and w.property("modified") != m:
                w.setProperty("modified", m)
                repolish(w)


class CheckRow(QWidget):
    """Case à cocher pour un réglage ±1 ou 0/1."""
    edited = Signal(object)

    def __init__(self, label: str, on_value=1, off_value=0, tip="", warn=False, parent=None):
        super().__init__(parent)
        self.on_value, self.off_value = on_value, off_value
        self.device_value = None
        self.title = label
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        self.box = QCheckBox(("⚠ " if warn else "") + label)
        if tip:
            self.setToolTip(tip)
        lay.addWidget(self.box)
        lay.addStretch()
        self._raw = None          # valeur carte inattendue (ni on ni off), conservée tant qu'on n'y touche pas
        self._label = self.box.text()
        self.box.toggled.connect(self._toggled)

    def _toggled(self, _):
        self._raw = None
        self.box.setText(self._label)
        self._mark()
        self.edited.emit(self.value())

    def value(self):
        if self._raw is not None:
            return self._raw
        return self.on_value if self.box.isChecked() else self.off_value

    def set_value(self, v):
        self.box.blockSignals(True)
        self.box.setChecked(v == self.on_value)
        self.box.blockSignals(False)
        if v not in (self.on_value, self.off_value):
            self._raw = v
            self.box.setText(self._label + "  — " + T("valeur carte inattendue : {v}").format(v=v))
        else:
            self._raw = None
            self.box.setText(self._label)
        self._mark()

    def set_device(self, v):
        self.device_value = v
        self.set_value(v)

    def modified(self):
        return self.device_value is not None and self.value() != self.device_value

    def _mark(self):
        self.box.setProperty("modified", "true" if self.modified() else "false")
        repolish(self.box)


class ComboRow(QWidget):
    edited = Signal(object)

    def __init__(self, label: str, items: list[str], tip="", warn=False, label_width=210, parent=None):
        super().__init__(parent)
        self.device_value = None
        self.title = label
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        l = QLabel(("⚠ " if warn else "") + label)
        l.setMinimumWidth(label_width)
        if warn:
            l.setObjectName("warnText")
        if tip:
            self.setToolTip(tip)
        self.combo = QComboBox()
        for i, it in enumerate(items):
            self.combo.addItem(it, i)
        lay.addWidget(l)
        lay.addStretch()
        lay.addWidget(self.combo)
        self.combo.currentIndexChanged.connect(lambda i: (self._mark(), self.edited.emit(self.value())))

    def value(self):
        d = self.combo.currentData()
        return int(d) if d is not None else self.combo.currentIndex()

    def set_value(self, v):
        v = int(v)
        self.combo.blockSignals(True)
        i = self.combo.findData(v)
        if i < 0:  # valeur que la liste ne connaît pas : on l'affiche au lieu de la remplacer
            self.combo.addItem(T("Valeur inconnue ({v})").format(v=v), v)
            i = self.combo.count() - 1
        self.combo.setCurrentIndex(i)
        self.combo.blockSignals(False)
        self._mark()

    def set_device(self, v):
        self.device_value = int(v)
        self.set_value(v)

    def modified(self):
        return self.device_value is not None and self.value() != self.device_value

    def _mark(self):
        self.combo.setProperty("modified", "true" if self.modified() else "false")
        repolish(self.combo)


class StatRow(QWidget):
    """Ligne « libellé ........ valeur unité » : ne peut pas se chevaucher, quelle que soit la largeur."""

    def __init__(self, label: str, unit: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        lay.setSpacing(6)
        self.lbl = QLabel(label)
        self.lbl.setObjectName("hint")
        self.lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)  # se réduit au lieu de déborder
        self.lbl.setToolTip(label)
        self.v = QLabel("—")
        self.v.setObjectName("midValue")
        self.v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.v.setMinimumWidth(70)
        self.u = QLabel(unit)
        self.u.setObjectName("unit")
        self.u.setMinimumWidth(52)
        self.lbl.setMinimumWidth(min(self.lbl.sizeHint().width(), 160))
        lay.addWidget(self.lbl, 1)
        lay.addWidget(self.v, 0)
        lay.addWidget(self.u, 0)

    def set(self, text: str, color: str | None = None):
        self.v.setText(text)
        self.v.setStyleSheet(f"color: {color};" if color else "")
