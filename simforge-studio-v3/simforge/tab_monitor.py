"""Onglet Moniteur : télémétrie HID à 1 kHz (position, vitesse, couple, courants, tension, températures, erreurs)."""
from __future__ import annotations

import csv
import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QFileDialog,
                               QScrollArea)

from . import ow_protocol as P
from .i18n import T
from .theme import C
from .widgets import card, hint, ValueReadout, WheelDial, CenterBar, StatRow

pg.setConfigOptions(antialias=False, background=C["panel"], foreground=C["dim"])

N = 16000          # ~16 s à 1 kHz
COLS = ["t", "pos", "vel", "iq", "tq", "vbus", "ibus", "ibrk"]


class Ring:
    """Tampons circulaires numpy, une colonne par grandeur."""

    def __init__(self, n=N):
        self.n = n
        self.d = {k: np.zeros(n) for k in COLS}
        self.i = 0
        self.count = 0

    def push(self, tm: P.Telemetry):
        i = self.i
        d = self.d
        d["t"][i], d["pos"][i], d["vel"][i], d["iq"][i] = tm.t, tm.pos, tm.vel * 360.0, tm.iq
        d["tq"][i], d["vbus"][i], d["ibus"][i], d["ibrk"][i] = tm.torque, tm.vbus, tm.ibus, tm.ibrake
        self.i = (i + 1) % self.n
        self.count = min(self.count + 1, self.n)

    def last(self, seconds, max_pts=2500):
        if not self.count:
            return None
        idx = (np.arange(self.i - self.count, self.i)) % self.n
        t = self.d["t"][idx]
        keep = t >= t[-1] - seconds
        idx = idx[keep]
        step = max(1, len(idx) // max_pts)
        idx = idx[::step]
        return {k: v[idx] for k, v in self.d.items()}

    def clear(self):
        self.i = self.count = 0


class MonitorTab(QWidget):
    WINDOW_S = 10.0

    def __init__(self, board, settings, parent=None):
        super().__init__(parent)
        self.b = board
        self.settings = settings
        self.ring = Ring()
        self._ranges = {}
        self._t_scale = 0.0
        self.last = None
        self.rate = 0.0
        self._rate_n, self._rate_t = 0, time.perf_counter()
        self.pk = None
        self.log_file = self.log_writer = None
        self.reset_peaks()

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # -------------------------------------------- colonne gauche
        col = QVBoxLayout()
        col.setSpacing(12)
        c, l = card(T("Volant"))
        self.dial = WheelDial(size=190)
        l.addWidget(self.dial, 0, Qt.AlignCenter)
        g = QGridLayout()
        self.r_angle = ValueReadout(T("Angle"), "°")
        self.r_speed = ValueReadout(T("Vitesse"), "°/s", big=False)
        self.r_torque = ValueReadout(T("Couple"), "N·m", big=False)
        self.r_iq = ValueReadout(T("Courant moteur"), "A", big=False)
        g.addWidget(self.r_angle, 0, 0, 1, 2)
        g.addWidget(self.r_speed, 1, 0)
        g.addWidget(self.r_torque, 1, 1)
        g.addWidget(self.r_iq, 2, 0)
        self.r_pct = ValueReadout(T("Du couple maxi"), "%", big=False)
        g.addWidget(self.r_pct, 2, 1)
        l.addLayout(g)
        self.tbar = CenterBar(color=C["blue"])
        l.addWidget(self.tbar)
        col.addWidget(c)

        c, l = card(T("Alimentation"))
        self.s = {}
        for k, lab, u in (("vbus", T("Tension bus"), "V"), ("ibus", T("Courant tiré (− = renvoyé)"), "A"),
                          ("ibrk", T("Courant résistance de freinage"), "A"),
                          ("pbrk", T("Puissance dans la résistance"), "W"),
                          ("pin", T("Puissance tirée sur l'alimentation"), "W"),
                          ("fet", T("Température transistors"), "°C"), ("mot", T("Température moteur"), "°C")):
            self.s[k] = StatRow(lab, u)
            l.addWidget(self.s[k])
        col.addWidget(c)

        c, l = card(T("Carte"))
        for k, lab, u in (("state", T("État de l'axe"), ""), ("rate", T("Rapports HID reçus"), "/s"),
                          ("btn", T("Boutons GPIO"), "")):
            self.s[k] = StatRow(lab, u)
            self.s[k].v.setMinimumWidth(40)
            l.addWidget(self.s[k])
        self.err = QLabel("")
        self.err.setWordWrap(True)
        l.addWidget(self.err)
        b = QPushButton(T("Effacer les erreurs"))
        b.clicked.connect(self.b.clear_errors)
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
        sc.setFixedWidth(400)
        root.addWidget(sc, 0)

        # -------------------------------------------- colonne droite
        right = QVBoxLayout()
        right.setSpacing(12)
        c, l = card(T("Courbes (10 s)"))
        self.p_pos = self._plot(T("Angle"), "°")
        self.c_pos = self.p_pos.plot(pen=pg.mkPen(C["accent"], width=2))
        self.p_tq = self._plot(T("Couple"), "N·m")
        self.c_tq = self.p_tq.plot(pen=pg.mkPen(C["blue"], width=1.6))
        self.p_i = self._plot(T("Courants"), "A")
        self.c_iq = self.p_i.plot(pen=pg.mkPen(C["dim"], width=1.2))
        self.c_ib = self.p_i.plot(pen=pg.mkPen(C["warn"], width=1.2))
        self.c_br = self.p_i.plot(pen=pg.mkPen(C["bad"], width=1.2))
        self.p_pw = self._plot(T("Tension bus"), "V")
        self.c_vb = self.p_pw.plot(pen=pg.mkPen(C["ok"], width=1.6))
        for p in (self.p_tq, self.p_i, self.p_pw):
            p.setXLink(self.p_pos)
        l.addWidget(self.p_pos, 3)
        l.addWidget(self.p_tq, 2)
        l.addWidget(self.p_i, 2)
        l.addWidget(self.p_pw, 2)
        leg = QLabel(T("Courants :") + f' <span style="color:{C["dim"]}">━ '
                     + T("courant moteur") + f'</span> &nbsp; <span style="color:{C["warn"]}">━ ' + T("courant tiré")
                     + f'</span> &nbsp; <span style="color:{C["bad"]}">━ ' + T("courant résistance") + "</span>")
        leg.setTextFormat(Qt.RichText)
        leg.setObjectName("hint")
        l.addWidget(leg)
        row = QHBoxLayout()
        self.b_log = QPushButton(T("Enregistrer en CSV…"))
        self.b_log.setCheckable(True)
        self.b_log.toggled.connect(self.toggle_log)
        self.b_pause = QPushButton(T("Figer"))
        self.b_pause.setCheckable(True)
        row.addWidget(self.b_log)
        row.addWidget(self.b_pause)
        row.addStretch()
        l.addLayout(row)
        right.addWidget(c, 4)

        c, l = card(T("Extrêmes depuis la remise à zéro"))
        g = QGridLayout()
        self.pk_rows = {}
        for i, (k, lab, u) in enumerate((("vmin", T("Tension mini (creux)"), "V"), ("vmax", T("Tension maxi (freinage)"), "V"),
                                         ("imax", T("Courant tiré maxi"), "A"), ("imin", T("Courant renvoyé maxi"), "A"),
                                         ("iq", T("Courant moteur maxi"), "A"), ("tq", T("Couple maxi"), "N·m"),
                                         ("spd", T("Vitesse maxi"), "°/s"), ("brk", T("Courant résistance maxi"), "A"))):
            s = StatRow(lab, u)
            self.pk_rows[k] = s
            g.addWidget(s, i // 2, i % 2)
        l.addLayout(g)
        hl = QHBoxLayout()
        b = QPushButton(T("Remettre à zéro"))
        b.clicked.connect(self.reset_peaks)
        hl.addWidget(b)
        hl.addWidget(hint(T("La tension maxi montre ce que le freinage fait monter : garde-la sous le seuil de "
                            "coupure haute.")), 1)
        l.addLayout(hl)
        right.addWidget(c, 0)
        root.addLayout(right, 1)

        self.b.telemetry.connect(self.on_batch)
        t = QTimer(self)
        t.timeout.connect(self.refresh)
        t.start(50)

    def _autoscale(self, plot, arrays, symmetric):
        lo = min(float(a.min()) for a in arrays)
        hi = max(float(a.max()) for a in arrays)
        if symmetric:
            m = max(abs(lo), abs(hi), 1e-3) * 1.15
            lo, hi = -m, m
        else:
            span = max(hi - lo, 0.2)
            lo, hi = lo - span * 0.15, hi + span * 0.15
        cur = self._ranges.get(id(plot))
        if cur:
            clo, chi = cur
            span = chi - clo
            # on ne change que si les données sortent du cadre ou n'en occupent plus qu'un tiers
            if lo >= clo and hi <= chi and (hi - lo) > span / 3:
                return
        self._ranges[id(plot)] = (lo, hi)
        plot.setYRange(lo, hi, padding=0)

    def _plot(self, title, unit=None):
        p = pg.PlotWidget()
        p.showGrid(x=True, y=True, alpha=0.15)
        p.setLabel("left", title, unit)
        p.setMenuEnabled(False)
        p.setMouseEnabled(x=False, y=False)
        p.getAxis("bottom").setStyle(showValues=False)
        p.getAxis("left").enableAutoSIPrefix(False)
        p.enableAutoRange(x=False, y=False)
        p.setXRange(-self.WINDOW_S, 0, padding=0)
        p.getAxis("left").setWidth(52)
        _plot = p.plot

        def plot(*a, **k):          # toutes les courbes : sous-échantillonnage « pics » + seulement la zone vue
            c = _plot(*a, **k)
            c.setDownsampling(auto=True, method="peak")
            c.setClipToView(True)
            return c
        p.plot = plot
        return p

    # ------------------------------------------------------------
    def param(self, path):
        r = self.settings.rows.get(path)
        return r.device if (r and r.read_ok) else None

    def reset_peaks(self):
        self.pk = {"vmin": None, "vmax": None, "imax": 0.0, "imin": 0.0, "iq": 0.0, "tq": 0.0, "spd": 0.0, "brk": 0.0}

    def toggle_log(self, on):
        if on:
            path, _ = QFileDialog.getSaveFileName(self, T("Fichier CSV"),
                                                  T("volant") + f"_{time.strftime('%Y%m%d_%H%M%S')}.csv", "CSV (*.csv)")
            if not path:
                self.b_log.setChecked(False)
                return
            self.log_file = open(path, "w", newline="", encoding="utf-8")
            self.log_writer = csv.writer(self.log_file, delimiter=";")
            self.log_writer.writerow(["t_s", "angle_deg", "vitesse_dps", "couple_Nm", "iq_A", "vbus_V", "ibus_A",
                                      "ibrake_A", "fet_C", "etat", "err_axe", "err_moteur", "err_codeur", "err_ctrl"])
            self._t0 = time.perf_counter()
            self.b_log.setText(T("■ Arrêter l'enregistrement"))
        else:
            if self.log_file:
                self.log_file.close()
            self.log_file = self.log_writer = None
            self.b_log.setText(T("Enregistrer en CSV…"))

    def on_batch(self, batch):
        pk = self.pk
        for tm in batch:
            if not self.b_pause.isChecked():
                self.ring.push(tm)
            pk["vmin"] = tm.vbus if pk["vmin"] is None else min(pk["vmin"], tm.vbus)
            pk["vmax"] = tm.vbus if pk["vmax"] is None else max(pk["vmax"], tm.vbus)
            pk["imax"] = max(pk["imax"], tm.ibus)
            pk["imin"] = min(pk["imin"], tm.ibus)
            pk["iq"] = max(pk["iq"], abs(tm.iq))
            pk["tq"] = max(pk["tq"], abs(tm.torque))
            pk["spd"] = max(pk["spd"], abs(tm.vel * 360))
            pk["brk"] = max(pk["brk"], tm.ibrake)
            if self.log_writer:
                self.log_writer.writerow([f"{tm.t - self._t0:.4f}", f"{tm.pos:.3f}", f"{tm.vel * 360:.1f}",
                                          f"{tm.torque:.3f}", f"{tm.iq:.3f}", f"{tm.vbus:.2f}", f"{tm.ibus:.2f}",
                                          f"{tm.ibrake:.2f}", "" if tm.fet_c is None else f"{tm.fet_c:.0f}", tm.state,
                                          f"0x{tm.axis_err:08X}", f"0x{tm.motor_err:08X}", f"0x{tm.enc_err:08X}",
                                          f"0x{tm.ctrl_err:08X}"])
        self._rate_n += len(batch)
        self.last = batch[-1]

    def refresh(self):
        now = time.perf_counter()
        if now - self._rate_t >= 1.0:
            self.rate = self._rate_n / (now - self._rate_t)
            self._rate_n, self._rate_t = 0, now
        tm = self.last
        if tm is None or not self.isVisible():
            return
        rng = self.param("axis.range") or (self.b.half_range * 2)
        mt = self.param("axis.maxtorque")
        pct = tm.torque / mt * 100 if mt else 0.0
        self.dial.set(tm.pos, rng, pct)
        self.r_angle.set(f"{tm.pos:+8.1f}")
        spd = tm.vel * 360
        self.r_speed.set(f"{spd:+7.0f}", C["bad"] if abs(spd) > self.b.guard_limit and self.b.guard_armed else None)
        self.r_torque.set(f"{tm.torque:+6.2f}")
        self.r_iq.set(f"{tm.iq:+6.2f}")
        self.r_pct.set(f"{pct:+5.0f}" if mt else "—", C["bad"] if abs(pct) >= 98 else None)
        self.tbar.set(pct)
        br = self.param("config.brake_resistance")
        self.s["vbus"].set(f"{tm.vbus:.2f}")
        self.s["ibus"].set(f"{tm.ibus:+.2f}")
        self.s["ibrk"].set(f"{tm.ibrake:.2f}")
        self.s["pbrk"].set(f"{tm.ibrake ** 2 * br:.1f}" if br else "—")
        self.s["pin"].set(f"{tm.vbus * tm.ibus:+.1f}")
        self.s["fet"].set("—" if tm.fet_c is None else f"{tm.fet_c:.0f}",
                          C["bad"] if (tm.fet_c or 0) >= 90 else C["warn"] if (tm.fet_c or 0) >= 70 else None)
        self.s["mot"].set("—" if tm.motor_c is None else f"{tm.motor_c:.0f}")
        self.s["state"].set(P.state_text(tm.state), C["ok"] if tm.state == P.CLOSED_LOOP else
                            C["blue"] if tm.state in P.CALIBRATING else None)
        self.s["rate"].set(f"{self.rate:.0f}", C["warn"] if self.rate < 500 else None)
        self.s["btn"].set(" ".join(str(i + 1) for i in range(64) if tm.buttons >> i & 1) or "—")
        errs = P.errors_of(tm)
        self.err.setText("\n".join(f"✖ {g} · {n} — {d}" for g, n, d in errs) if errs else T("Aucune erreur."))
        self.err.setStyleSheet(f"color: {C['bad'] if errs else C['ok']};")
        pk = self.pk
        for k, fmt in (("vmin", "{:.2f}"), ("vmax", "{:.2f}"), ("imax", "{:+.2f}"), ("imin", "{:+.2f}"),
                       ("iq", "{:.2f}"), ("tq", "{:.2f}"), ("spd", "{:.0f}"), ("brk", "{:.2f}")):
            v = pk[k]
            self.pk_rows[k].set("—" if v is None else fmt.format(v))
        ov = self.param("config.dc_bus_overvoltage_trip_level")
        if pk["vmax"] is not None and ov:
            self.pk_rows["vmax"].set(f"{pk['vmax']:.2f}", C["bad"] if pk["vmax"] > ov - 1.5 else None)
        if self.b_pause.isChecked():
            return
        d = self.ring.last(self.WINDOW_S)
        if d is None:
            return
        x = d["t"] - d["t"][-1]
        self.c_pos.setData(x, d["pos"])
        self.c_tq.setData(x, d["tq"])
        self.c_iq.setData(x, d["iq"])
        self.c_vb.setData(x, d["vbus"])
        self.c_ib.setData(x, d["ibus"])
        self.c_br.setData(x, d["ibrk"])
        # échelles Y recalculées 2 fois par seconde seulement, avec hystérésis : redessiner les axes à chaque
        # image coûtait plus cher que les courbes
        now = time.perf_counter()
        if now - self._t_scale > 0.5:
            self._t_scale = now
            for plot, arrays, sym in ((self.p_pos, (d["pos"],), True), (self.p_tq, (d["tq"],), True),
                                      (self.p_i, (d["iq"], d["ibus"], d["ibrk"]), True),
                                      (self.p_pw, (d["vbus"],), False)):
                self._autoscale(plot, arrays, sym)
