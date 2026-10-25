"""Onglet Joy tester : axes (valeur, pas, pas max), boutons, chapeaux, courbe, journal CSV."""
from __future__ import annotations

from .i18n import T

import csv
import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
                               QComboBox, QFileDialog, QCheckBox)

from .theme import C
from .widgets import card, hint, Led, AxisBar

AXIS_NAMES = []  # SDL ne donne pas le nom des axes DirectInput : on numérote, sans supposer X, Y, Rz…
AXIS_COLORS = [C["accent"], "#e5484d", C["blue"], "#c2c24c", "#b07ce8", "#3fb7b0", "#5a7cf2", "#e86fbf"]
HAT = {0: "·", 1: "↑", 2: "→", 3: "↗", 4: "↓", 6: "↘", 8: "←", 9: "↖", 12: "↙"}


class JoyTab(QWidget):
    def __init__(self, sdl, parent=None):
        super().__init__(parent)
        self.sdl = sdl
        self.prev = None
        self.maxstep = []
        self.hist = deque(maxlen=3000)
        self.log = None
        self.logw = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)
        top = QHBoxLayout()
        top.addWidget(QLabel(T("Périphérique :")))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(320)
        top.addWidget(self.combo)
        b = QPushButton(T("Actualiser"))
        b.clicked.connect(self.refresh_devices)
        top.addWidget(b)
        self.b_reset = QPushButton(T("RAZ pas max"))
        self.b_reset.clicked.connect(lambda: setattr(self, "maxstep", [0] * len(self.maxstep)))
        top.addWidget(self.b_reset)
        self.b_log = QPushButton(T("Journal CSV…"))
        self.b_log.setCheckable(True)
        self.b_log.toggled.connect(self.toggle_log)
        top.addWidget(self.b_log)
        top.addStretch()
        self.status = QLabel("")
        self.status.setObjectName("hint")
        top.addWidget(self.status)
        root.addLayout(top)

        if not sdl.ok:
            root.addWidget(hint(T("SDL2 indisponible : {e}. Lance l'appli avec SimForge Studio.bat pour installer "
                                  "les dépendances.").format(e=sdl.error)))

        mid = QHBoxLayout()
        mid.setSpacing(12)
        c, l = card(T("Axes  —  valeur brute (-32768…32767), pas entre deux lectures, pas max"))
        self.axgrid = QGridLayout()
        self.axgrid.setHorizontalSpacing(10)
        l.addLayout(self.axgrid)
        self.ax_widgets = []
        l.addStretch()
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setYRange(-32768, 32767)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.getAxis("bottom").setStyle(showValues=False)
        self.curves = []
        l.addWidget(self.plot, 1)
        mid.addWidget(c, 3)

        right = QVBoxLayout()
        c2, l2 = card(T("Boutons"))
        self.btngrid = QGridLayout()
        self.btngrid.setSpacing(4)
        l2.addLayout(self.btngrid)
        l2.addStretch()
        self.btn_leds = []
        right.addWidget(c2, 3)
        c3, l3 = card(T("Chapeaux (POV)"))
        self.hatrow = QHBoxLayout()
        l3.addLayout(self.hatrow)
        self.hat_lbls = []
        right.addWidget(c3, 0)
        mid.addLayout(right, 2)
        root.addLayout(mid, 1)
        root.addWidget(hint(T("Lecture DirectInput, comme un jeu. Le volant FFBeast apparaît sous le nom "
                            "« FFBeast Wheel ». « Pas » = variation entre deux lectures (≈100 Hz) : "
                            "au repos il doit être nul ou de quelques unités.")))

        self.combo.currentIndexChanged.connect(self.open_index)
        self.refresh_devices()
        self.t = QTimer(self)
        self.t.timeout.connect(self.tick)
        self.t.start(10)

    # -------------------------------------------------------------
    def refresh_devices(self):
        cur = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        names = self.sdl.devices()
        self.combo.addItems(names)
        idx = next((i for i, n in enumerate(names) if n == cur), -1)
        if idx < 0:
            idx = next((i for i, n in enumerate(names) if "ffbeast" in n.lower()), 0 if names else -1)
        self.combo.blockSignals(False)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
            self.open_index(idx)
        else:
            self.status.setText(T("Aucun joystick détecté"))

    def open_index(self, idx):
        if idx < 0:
            return
        if self.sdl.open(idx):
            self.status.setText("")
        else:
            self.status.setText(T("Ouverture impossible : {e}").format(e=self.sdl.error))
        self.prev = None
        self._layout_for(None)

    def _layout_for(self, data):
        n_ax = len(data[0]) if data else 0
        n_bt = len(data[1]) if data else 0
        n_hat = len(data[2]) if data else 0
        if len(self.ax_widgets) == n_ax and len(self.btn_leds) == n_bt and len(self.hat_lbls) == n_hat:
            return
        for lay in (self.axgrid, self.btngrid, self.hatrow):
            while lay.count():
                it = lay.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
        self.ax_widgets, self.btn_leds, self.hat_lbls = [], [], []
        for c in self.curves:
            self.plot.removeItem(c)
        self.curves = []
        self.hist.clear()
        self.maxstep = [0] * n_ax
        for j, h in enumerate([T("Axe"), "", T("Valeur"), T("Pas"), T("Pas max")]):
            lab = QLabel(h)
            lab.setObjectName("hint")
            self.axgrid.addWidget(lab, 0, j)
        for i in range(n_ax):
            col = AXIS_COLORS[i % len(AXIS_COLORS)]
            name = QCheckBox(AXIS_NAMES[i] if i < len(AXIS_NAMES) else T("Axe {n}").format(n=i + 1))
            name.setChecked(i == 0)
            name.setStyleSheet(f"color: {col};")
            bar = AxisBar(color=col)
            vals = [QLabel("0") for _ in range(3)]
            for v in vals:
                v.setObjectName("midValue")
                v.setAlignment(Qt.AlignRight)
                v.setMinimumWidth(70)
            self.axgrid.addWidget(name, i + 1, 0)
            self.axgrid.addWidget(bar, i + 1, 1)
            for j, v in enumerate(vals):
                self.axgrid.addWidget(v, i + 1, 2 + j)
            self.axgrid.setColumnStretch(1, 1)
            self.ax_widgets.append((name, bar, *vals))
            self.curves.append(self.plot.plot(pen=pg.mkPen(col, width=1.5)))
        cols = 8
        for i in range(n_bt):
            box = QWidget()
            hl = QHBoxLayout(box)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(3)
            led = Led(C["ok"], 10)
            led.set(C["ok"], False)
            t = QLabel(str(i + 1))
            t.setObjectName("hint")
            hl.addWidget(led)
            hl.addWidget(t)
            self.btngrid.addWidget(box, i // cols, i % cols)
            self.btn_leds.append(led)
        for i in range(n_hat):
            lab = QLabel("·")
            lab.setObjectName("bigValue")
            lab.setAlignment(Qt.AlignCenter)
            lab.setMinimumWidth(50)
            self.hatrow.addWidget(lab)
            self.hat_lbls.append(lab)
        self.hatrow.addStretch()

    def toggle_log(self, on):
        if on:
            path, _ = QFileDialog.getSaveFileName(self, T("Journal"), f"joy_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                                                  "CSV (*.csv)")
            if not path:
                self.b_log.setChecked(False)
                return
            self.log = open(path, "w", newline="", encoding="utf-8")
            self.logw = csv.writer(self.log, delimiter=";")
            self._t0 = time.perf_counter()
            self._log_header = False
            self.b_log.setText(T("■ Arrêter le journal"))
        else:
            if self.log:
                self.log.close()
            self.log = self.logw = None
            self.b_log.setText(T("Journal CSV…"))

    def tick(self):
        if not self.sdl.ok:
            return
        if self.sdl.poll_hotplug():
            self.refresh_devices()
        data = self.sdl.read()
        if data is None:
            return
        self._layout_for(data)
        axes, btns, hats = data
        if self.prev and len(self.prev) == len(axes):
            for i, v in enumerate(axes):
                self.maxstep[i] = max(self.maxstep[i], abs(v - self.prev[i]))
        for i, v in enumerate(axes):
            name, bar, lv, ls, lm = self.ax_widgets[i]
            bar.set((v + 32768) / 65535)
            lv.setText(str(v))
            ls.setText(str(abs(v - self.prev[i])) if self.prev and i < len(self.prev) else "0")
            lm.setText(str(self.maxstep[i]))
        self.prev = list(axes)
        for led, b in zip(self.btn_leds, btns):
            led.set(C["ok"], b)
        for lab, h in zip(self.hat_lbls, hats):
            lab.setText(HAT.get(h, str(h)))
        self.hist.append(axes)
        if len(self.hist) % 3 == 0:
            for i, c in enumerate(self.curves):
                if self.ax_widgets[i][0].isChecked():
                    c.setData([h[i] for h in self.hist])
                else:
                    c.setData([])
        if self.logw:
            if not self._log_header:
                self.logw.writerow(["t_s"] + [f"axe{i + 1}" for i in range(len(axes))] +
                                   [f"b{i + 1}" for i in range(len(btns))] + [f"pov{i + 1}" for i in range(len(hats))])
                self._log_header = True
            self.logw.writerow([f"{time.perf_counter() - self._t0:.4f}", *axes, *[int(b) for b in btns], *hats])
