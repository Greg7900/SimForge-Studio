"""Onglet Codeur : compteurs ODrive (lus par le port série) et qualité du signal (position HID à 1 kHz)."""
from __future__ import annotations

import time
from collections import deque

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QScrollArea,
                               QCheckBox, QDoubleSpinBox, QPlainTextEdit)

from . import ow_protocol as P
from .i18n import T
from .theme import C
from .widgets import card, hint, StatRow

POLL = ["axis0.encoder.shadow_count", "axis0.encoder.count_in_cpr", "axis0.encoder.pos_estimate",
        "axis0.encoder.vel_estimate", "axis0.encoder.is_ready", "axis0.encoder.index_found",
        "axis0.encoder.error", "axis0.encoder.config.phase_offset", "axis.zhits", "axis.zglitch"]
CFG = ["axis0.encoder.config.mode", "axis0.encoder.config.cpr", "axis0.encoder.config.direction",
       "axis0.encoder.config.use_index", "axis0.encoder.config.pre_calibrated", "axis0.encoder.config.bandwidth",
       "axis0.motor.config.pole_pairs"]


def _f(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


class EncoderTab(QWidget):
    def __init__(self, board, settings, parent=None):
        super().__init__(parent)
        self.b = board
        self.settings = settings
        self.vals = {}
        self.t = deque(maxlen=12000)
        self.p = deque(maxlen=12000)
        self.prev = None
        self.jumps = 0
        self.samples = 0
        self.max_dev = 0.0
        self.z_start = None

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)
        col = QVBoxLayout()
        col.setSpacing(12)

        c, l = card(T("Compteurs ODrive (port série)"))
        self.poll = QCheckBox(T("Lecture continue (4 fois par seconde)"))
        self.poll.setChecked(True)
        l.addWidget(self.poll)
        self.s = {}
        for k, lab, u in (("axis0.encoder.shadow_count", T("Compteur total"), T("pts")),
                          ("axis0.encoder.count_in_cpr", T("Position dans le tour"), T("pts")),
                          ("axis0.encoder.pos_estimate", T("Position estimée"), T("tours")),
                          ("axis0.encoder.vel_estimate", T("Vitesse estimée"), T("tr/s")),
                          ("axis0.encoder.is_ready", T("Codeur calé (prêt)"), ""),
                          ("axis0.encoder.index_found", T("Index Z trouvé"), ""),
                          ("axis0.encoder.error", T("Erreur codeur"), ""),
                          ("axis0.encoder.config.phase_offset", T("Décalage de phase (calage)"), T("pts"))):
            self.s[k] = StatRow(lab, u)
            l.addWidget(self.s[k])
        col.addWidget(c)

        c, l = card(T("Configuration"))
        for k, lab, u in (("axis0.encoder.config.mode", T("Type"), ""), ("axis0.encoder.config.cpr", "CPR", ""),
                          ("axis0.encoder.config.direction", T("Sens"), ""),
                          ("axis0.encoder.config.use_index", T("Index utilisé"), ""),
                          ("axis0.encoder.config.pre_calibrated", T("Calage conservé"), ""),
                          ("axis0.encoder.config.bandwidth", T("Bande passante"), "rad/s"),
                          ("axis0.motor.config.pole_pairs", T("Paires de pôles"), ""),
                          ("cpr_pp", T("Points par pas électrique"), T("pts"))):
            self.s[k] = StatRow(lab, u)
            l.addWidget(self.s[k])
        self.cfg_note = hint("")
        l.addWidget(self.cfg_note)
        b = QPushButton(T("Relire la configuration"))
        b.clicked.connect(lambda: self.b.read(CFG, "enc_cfg"))
        hl = QHBoxLayout()
        hl.addWidget(b)
        hl.addStretch()
        l.addLayout(hl)
        col.addWidget(c)

        c, l = card(T("Signal Z (index)"))
        l.addWidget(hint(T("Le firmware compte les impulsions Z reçues, même si l'index n'est pas utilisé. Avec une "
                           "courroie 72/16, le Z doit rester débranché : le compteur doit rester à 0.")))
        self.s["axis.zhits"] = StatRow(T("Impulsions Z acceptées"), "")
        self.s["axis.zglitch"] = StatRow(T("Parasites Z rejetés"), "")
        l.addWidget(self.s["axis.zhits"])
        l.addWidget(self.s["axis.zglitch"])
        b = QPushButton(T("Remettre les compteurs Z à zéro"))
        b.clicked.connect(self._z_reset)
        hl = QHBoxLayout()
        hl.addWidget(b)
        hl.addStretch()
        l.addLayout(hl)
        col.addWidget(c)
        col.addStretch()
        w = QWidget()
        w.setLayout(col)
        col.setContentsMargins(0, 0, 6, 0)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setWidget(w)
        sc.setFixedWidth(380)
        root.addWidget(sc, 0)

        right = QVBoxLayout()
        right.setSpacing(12)
        c, l = card(T("Qualité du signal (position remontée à 1 kHz)"))
        l.addWidget(hint(T("Chaque milliseconde, la carte envoie la position et la vitesse. Un saut de position qui ne "
                           "correspond pas à la vitesse mesurée trahit des impulsions perdues ou parasites (câble "
                           "codeur trop long, masse, pas de résistances de tirage). Tourne le volant à la main, moteur "
                           "au repos.")))
        g = QGridLayout()
        self.q_samples = StatRow(T("Échantillons analysés"), "")
        self.q_jumps = StatRow(T("Sauts anormaux"), "")
        self.q_dev = StatRow(T("Plus gros écart position/vitesse"), "°")
        g.addWidget(self.q_samples, 0, 0)
        g.addWidget(self.q_jumps, 0, 1)
        g.addWidget(self.q_dev, 1, 0)
        th = QHBoxLayout()
        th.addWidget(QLabel(T("Seuil de saut")))
        self.thr = QDoubleSpinBox()
        self.thr.setRange(0.05, 90)
        self.thr.setDecimals(2)
        self.thr.setValue(2.0)
        self.thr.setSuffix(" °")
        th.addWidget(self.thr)
        th.addStretch()
        g.addLayout(th, 1, 1)
        l.addLayout(g)
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel("left", T("Angle"), "°")
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.getAxis("bottom").setStyle(showValues=False)
        self.plot.getAxis("left").enableAutoSIPrefix(False)
        self.plot.enableAutoRange(x=False, y=False)
        self.plot.setXRange(-10, 0, padding=0)
        self.plot.getAxis("left").setWidth(52)
        self._yr = None
        self._t_yr = 0.0
        self.curve = self.plot.plot(pen=pg.mkPen(C["accent"], width=1.6))
        self.curve.setDownsampling(auto=True, method="peak")
        self.curve.setClipToView(True)
        self.marks = pg.ScatterPlotItem(size=8, brush=pg.mkBrush(C["bad"]), pen=None)
        self.plot.addItem(self.marks)
        self.jump_pts = deque(maxlen=200)
        l.addWidget(self.plot, 1)
        self.jlog = QPlainTextEdit()
        self.jlog.setObjectName("console")
        self.jlog.setReadOnly(True)
        self.jlog.setMaximumBlockCount(300)
        self.jlog.setMaximumHeight(130)
        l.addWidget(self.jlog)
        b = QPushButton(T("Remettre à zéro"))
        b.clicked.connect(self.reset_q)
        hl = QHBoxLayout()
        hl.addWidget(b)
        hl.addStretch()
        l.addLayout(hl)
        right.addWidget(c, 1)
        root.addLayout(right, 1)

        self.b.values.connect(self.on_values)
        self.b.telemetry.connect(self.on_batch)
        self.b.link_changed.connect(lambda i: i.get("serial") and self.b.read(CFG, "enc_cfg"))
        t = QTimer(self)
        t.timeout.connect(self._poll)
        t.start(250)
        t2 = QTimer(self)
        t2.timeout.connect(self.refresh)
        t2.start(50)

    def showEvent(self, e):
        if self.b.serial_ok:
            self.b.read(CFG, "enc_cfg")
        super().showEvent(e)

    # ------------------------------------------------------------ série
    def _poll(self):
        if not (self.isVisible() and self.poll.isChecked() and self.b.serial_ok):
            return
        if self.b.ser.q.qsize() > 0:          # ne pas encombrer la file des réglages
            return
        self.b.read(POLL, "enc_poll")

    def _z_reset(self):
        self.b.write("axis.zhits", 0)
        self.b.write("axis.zglitch", 0)
        QTimer.singleShot(300, lambda: self.b.read(["axis.zhits", "axis.zglitch"], "enc_poll"))

    def on_values(self, vals, tag):
        if tag not in ("enc_poll", "enc_cfg", "all"):
            return
        self.vals.update({k: v for k, v in vals.items() if v is not None})
        g = self.vals.get
        for k in POLL:
            if k in vals and k in self.s:
                v = vals[k]
                if v is None:
                    self.s[k].set("—")
                elif k == "axis0.encoder.error":
                    e = int(_f(v) or 0)
                    names = [n for n, _d in P.decode("encoder", e)]
                    self.s[k].set(", ".join(names) if names else "0", C["bad"] if e else C["ok"])
                elif k in ("axis0.encoder.is_ready", "axis0.encoder.index_found"):
                    on = v.strip() == "1"
                    self.s[k].set(T("oui") if on else T("non"),
                                  (C["ok"] if on else C["warn"]) if k.endswith("is_ready") else None)
                elif k in ("axis0.encoder.pos_estimate", "axis0.encoder.vel_estimate"):
                    x = _f(v)
                    self.s[k].set(f"{x:+.4f}" if x is not None else v)
                elif k == "axis.zhits":
                    n = int(_f(v) or 0)
                    self.s[k].set(str(n), C["warn"] if n and g("axis0.encoder.config.use_index") == "0" else None)
                else:
                    self.s[k].set(v)
        modes = dict(P.ENC_MODES)
        for k in CFG:
            v = g(k)
            if v is None or k not in self.s:
                continue
            if k == "axis0.encoder.config.mode":
                self.s[k].set(modes.get(int(_f(v) or 0), v))
            elif k in ("axis0.encoder.config.use_index", "axis0.encoder.config.pre_calibrated"):
                self.s[k].set(T("oui") if v.strip() == "1" else T("non"))
            elif k == "axis0.encoder.config.direction":
                d = int(_f(v) or 0)
                self.s[k].set({1: "+1", -1: "−1", 0: T("0 (pas encore calibré)")}.get(d, v),
                              C["warn"] if d == 0 else None)
            else:
                x = _f(v)
                self.s[k].set(f"{x:g}" if x is not None else v)
        cpr, pp = _f(g("axis0.encoder.config.cpr")), _f(g("axis0.motor.config.pole_pairs"))
        if cpr and pp:
            per = cpr / pp
            self.s["cpr_pp"].set(f"{per:.0f}")
            notes = []
            if per < 50:
                notes.append(T("Moins de 50 points par pas électrique : résolution trop faible pour un couple "
                               "régulier."))
            if g("axis0.encoder.config.mode") == "0" and g("axis0.encoder.config.use_index") == "0" \
                    and g("axis0.encoder.config.pre_calibrated") == "1":
                notes.append(T("⚠ Calage conservé sans index : dangereux avec un codeur incrémental."))
            self.cfg_note.setText(" ".join(notes))
            self.cfg_note.setStyleSheet(f"color: {C['warn']};" if notes else "")

    # ------------------------------------------------------------ HID
    def reset_q(self):
        self.prev = None
        self.jumps = 0
        self.samples = 0
        self.max_dev = 0.0
        self.jump_pts.clear()
        self.jlog.clear()

    def on_batch(self, batch):
        thr = self.thr.value()
        hr = self.b.half_range or 450.0
        for tm in batch:
            self.t.append(tm.t)
            self.p.append(tm.pos)
            if self.prev is not None:
                pt, pp, pv = self.prev
                dt = tm.t - pt
                sat = abs(tm.pos_raw) >= 32700 or abs(pp) >= hr * 0.998
                if 0 < dt < 0.02 and not sat:
                    self.samples += 1
                    # la vitesse HID est celle de l'encodeur (sens éventuellement opposé à la position) :
                    # on compare en valeur absolue avec la vitesse moyenne des deux échantillons
                    expect = abs((pv + tm.vel) / 2 * 360.0 * dt)
                    dev = abs(abs(tm.pos - pp) - expect)
                    self.max_dev = max(self.max_dev, dev)
                    if dev > thr:
                        self.jumps += 1
                        self.jump_pts.append((tm.t, tm.pos))
                        self.jlog.appendPlainText(
                            f"{time.strftime('%H:%M:%S')}  Δ={tm.pos - pp:+.2f}°  " +
                            T("attendu ±{e}°").format(e=f"{expect:.2f}") + f"  v={tm.vel * 360:+.0f}°/s")
            self.prev = (tm.t, tm.pos, tm.vel)

    def refresh(self):
        if not self.isVisible() or not self.t:
            return
        self.q_samples.set(str(self.samples))
        self.q_jumps.set(str(self.jumps), C["bad"] if self.jumps else C["ok"])
        self.q_dev.set(f"{self.max_dev:.2f}")
        t1 = self.t[-1]
        n = len(self.t)
        k = max(1, n // 2500)
        tt = np.array(list(self.t)[::k]) - t1
        pp = np.array(list(self.p)[::k])
        m = tt >= -10
        self.curve.setData(tt[m], pp[m])
        jp = [(t - t1, p) for t, p in self.jump_pts if t1 - t <= 10]
        self.marks.setData([x for x, _ in jp], [y for _, y in jp])
        now = time.perf_counter()
        if len(pp[m]) and now - self._t_yr > 0.5:
            self._t_yr = now
            lo, hi = float(pp[m].min()), float(pp[m].max())
            span = max(hi - lo, 5.0)
            lo, hi = lo - span * 0.15, hi + span * 0.15
            if not self._yr or lo < self._yr[0] or hi > self._yr[1] or (hi - lo) < (self._yr[1] - self._yr[0]) / 3:
                self._yr = (lo, hi)
                self.plot.setYRange(lo, hi, padding=0)
