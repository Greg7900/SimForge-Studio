"""Onglet Overlay : petite fenêtre transparente toujours au premier plan, au-dessus du jeu.

Avec Odrive-Wheel, toutes les valeurs viennent de la télémétrie HID à 1 kHz : couple réel en N·m, courants,
tension, puissance dans la résistance de freinage, température des transistors.
"""
from __future__ import annotations

import json
import time
from collections import deque

from PySide6.QtCore import Qt, QTimer, QPoint, QSize, QEvent
from PySide6.QtGui import QColor, QPainter, QFont, QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
                               QCheckBox, QComboBox, QSpinBox, QApplication, QScrollArea, QFrame)

from . import ow_protocol as P
from . import i18n
from .i18n import T
from .theme import C
from .widgets import card, hint, SettingRow

# clé, libellé, unité
METRICS = [
    ("angle", T("Angle"), "°"),
    ("speed", T("Vitesse"), "°/s"),
    ("torque", T("Couple"), "N·m"),
    ("torque_pct", T("Couple en % du maxi"), "%"),
    ("torque_bar", T("Barre de couple"), ""),
    ("torque_peak", T("Couple crête (3 s)"), "N·m"),
    ("clipping", T("Saturation du couple (5 s)"), "%"),
    ("iq", T("Courant moteur"), "A"),
    ("vbus", T("Tension bus"), "V"),
    ("vsag", T("Tension mini (10 s)"), "V"),
    ("ibus", T("Courant tiré"), "A"),
    ("pin", T("Puissance tirée"), "W"),
    ("ibrake", T("Courant résistance de freinage"), "A"),
    ("pbrake", T("Puissance résistance (moy. 5 s)"), "W"),
    ("fet", T("Température transistors"), "°C"),
    ("range_used", T("Course utilisée"), "%"),
    ("fps", T("Rapports / s"), ""),
    ("status", T("État (connexion / moteur / erreurs)"), ""),
]
DEFAULT = {"show": ["angle", "torque", "torque_bar", "clipping", "vbus", "ibus", "pbrake", "status"],
           "opacity": 85, "font": 13, "horizontal": False, "clickthrough": False, "pos": None,
           "curves": False, "curve_s": 10}


def _valid(key, v):
    """Préférence relue du registre : même type que la valeur par défaut (pos : None ou [x, y])."""
    if key == "pos":
        return v is None or (isinstance(v, list) and len(v) == 2 and all(isinstance(c, (int, float)) for c in v))
    return isinstance(v, type(DEFAULT[key]))


class OverlayPanel(QWidget):
    """Rendu de l'overlay (aperçu et fenêtre flottante). Mode valeurs ou mode courbes.

    rows : [(libellé, texte, couleur, kind, extra)]
      kind "text" : extra = None ou (points [(t, v)], ymin, ymax) pour la courbe
      kind "bar"  : extra = valeur -100..100
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.font_pt = 13
        self.horizontal = False
        self.curves = False
        self.window_s = 10.0
        self.bg_alpha = 200
        self.setMinimumSize(120, 40)

    def set_rows(self, rows):
        self.rows = rows
        self.updateGeometry()
        self.adjustSize()
        self.update()

    def _metrics(self):
        from PySide6.QtGui import QFontMetrics
        f = QFont()
        f.setFamilies(["Consolas", "DejaVu Sans Mono"])
        f.setPointSize(self.font_pt)
        f.setBold(True)
        lf = QFont()
        lf.setPointSize(max(7, int(self.font_pt * 0.62)))
        return f, lf, QFontMetrics(f), QFontMetrics(lf)

    def _spark_h(self, fm):
        return int(fm.height() * 1.7) if self.curves else 0

    def _colw(self, fm, lm):
        out = []
        for lab, val, col, kind, extra in self.rows:
            w = max(fm.horizontalAdvance(val or ""), lm.horizontalAdvance(lab.upper()), 60)
            if kind == "bar":
                w = max(w, 110)
            if self.curves and kind == "text" and extra:
                w = max(w, int(fm.height() * 7))
            out.append(w + 18)
        return out

    def sizeHint(self):
        from PySide6.QtCore import QSize
        f, lf, fm, lm = self._metrics()
        pad = 12
        if not self.rows:
            return super().sizeHint()
        sh = self._spark_h(fm)
        if self.horizontal:
            return QSize(int(pad + sum(self._colw(fm, lm))), int(lm.height() + fm.height() + sh + pad * 2 + 4))
        w = max(max(lm.horizontalAdvance(r[0].upper()) for r in self.rows) + fm.horizontalAdvance("+0000.0 °/s")
                + pad * 4, 220 if not self.curves else int(fm.height() * 14))
        h = pad * 2
        for lab, val, col, kind, extra in self.rows:
            h += fm.height() + 6 + (sh + 4 if (kind == "text" and extra and self.curves) else 0)
        return QSize(int(w), int(h))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QColor(C["bg"])
        bg.setAlpha(self.bg_alpha)
        p.setPen(QColor(C["line"]))
        p.setBrush(bg)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        f, lf, fm, lm = self._metrics()
        pad = 12
        sh = self._spark_h(fm)
        if self.horizontal:
            x = pad
            for (lab, val, col, kind, extra), colw in zip(self.rows, self._colw(fm, lm)):
                p.setFont(lf)
                p.setPen(QColor(C["dim"]))
                p.drawText(int(x), pad + lm.ascent(), lab.upper())
                y = pad + lm.height() + 2
                if kind == "bar":
                    self._bar(p, x, y + 4, colw - 18, fm.height() - 8, extra)
                else:
                    p.setFont(f)
                    p.setPen(QColor(col or C["text"]))
                    p.drawText(int(x), int(y + fm.ascent()), val)
                    if self.curves and extra:
                        self._spark(p, x, y + fm.height() + 2, colw - 18, sh, extra, col)
                x += colw
            return
        y = pad
        for lab, val, col, kind, extra in self.rows:
            h = fm.height()
            p.setFont(lf)
            p.setPen(QColor(C["dim"]))
            p.drawText(pad, int(y + (h + lm.ascent()) / 2 - 2), lab.upper())
            if kind == "bar":
                bx = self.width() * 0.45
                self._bar(p, bx, y + 4, self.width() - bx - pad, h - 8, extra)
            else:
                p.setFont(f)
                p.setPen(QColor(col or C["text"]))
                tw = fm.horizontalAdvance(val)
                p.drawText(int(self.width() - pad - tw), int(y + fm.ascent()), val)
            y += h + 6
            if kind == "text" and extra and self.curves:
                self._spark(p, pad, y - 2, self.width() - 2 * pad, sh, extra, col)
                y += sh + 4

    def _spark(self, p, x, y, w, h, extra, col):
        pts, lo, hi = extra
        p.setPen(QColor(C["line"]))
        p.setBrush(QColor(C["panel"]))
        p.drawRect(int(x), int(y), int(w), int(h))
        if hi <= lo:
            hi = lo + 1
        if lo < 0 < hi:  # ligne du zéro
            zy = y + h - (0 - lo) / (hi - lo) * h
            p.setPen(QColor(C["line"]))
            p.drawLine(int(x), int(zy), int(x + w), int(zy))
        if len(pts) < 2:
            return
        from PySide6.QtGui import QPen, QPolygonF
        from PySide6.QtCore import QPointF
        t1 = pts[-1][0]
        poly = QPolygonF()
        for t, v in pts:
            px = x + w - (t1 - t) / self.window_s * w
            if px < x:
                continue
            vv = max(lo, min(hi, v))
            poly.append(QPointF(px, y + h - (vv - lo) / (hi - lo) * h))
        p.setPen(QPen(QColor(col or C["accent"]), 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(poly)

    @staticmethod
    def _bar(p, x, y, w, h, v):
        v = max(-100.0, min(100.0, v or 0.0))
        p.setPen(QColor(C["line"]))
        p.setBrush(QColor(C["panel"]))
        p.drawRect(int(x), int(y), int(w), int(h))
        mid = x + w / 2
        bw = w / 2 * v / 100
        col = QColor(C["bad"] if abs(v) >= 98 else C["blue"])
        p.fillRect(int(min(mid, mid + bw)), int(y + 1), int(abs(bw)), int(h - 1), col)
        p.setPen(QColor(C["dim"]))
        p.drawLine(int(mid), int(y - 2), int(mid), int(y + h + 2))



class OverlayPreview(QWidget):
    """Aperçu dans la page : le panneau est dessiné à sa taille réelle, réduit jusqu'à 70 % pour tenir en largeur,
    et au-delà la zone défile (avant, en disposition horizontale, il était coupé après les premières mesures)."""
    MIN_SCALE = 0.7

    def __init__(self, parent=None):
        super().__init__(parent)
        self.panel = OverlayPanel(self)         # modèle, jamais affiché tel quel
        self.panel.hide()
        self.area = QScrollArea()               # c'est elle qu'on place dans la page
        self.area.setWidget(self)
        self.area.setWidgetResizable(False)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        self.area.viewport().installEventFilter(self)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Resize:
            self._fit()
        return False

    def set_rows(self, rows):
        self.panel.rows = rows
        self._fit()
        self.update()

    def _fit(self):
        n = self.panel.sizeHint()
        if n.width() <= 0 or n.height() <= 0:
            return
        k = min(1.0, max(self.MIN_SCALE, self.area.viewport().width() / n.width()))
        size = QSize(int(n.width() * k), int(n.height() * k))
        if self.size() != size:
            self.setFixedSize(size)
        sb = self.area.horizontalScrollBar().sizeHint().height() if size.width() > self.area.viewport().width() else 0
        self.area.setFixedHeight(size.height() + sb)

    def paintEvent(self, _):
        n = self.panel.sizeHint()
        if n.width() <= 0 or n.height() <= 0:
            return
        self.panel.resize(n)
        dpr = self.devicePixelRatioF()
        pm = QPixmap(int(n.width() * dpr), int(n.height() * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent)
        self.panel.render(pm)
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(self.rect(), pm)

class OverlayWindow(QWidget):
    def __init__(self, on_moved):
        super().__init__(None)
        self.on_moved = on_moved
        self.setWindowTitle("SimForge overlay")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.panel = OverlayPanel(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.panel)
        self._drag = None
        self.set_clickthrough(False)

    def set_clickthrough(self, on: bool):
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        if on:
            flags |= Qt.WindowTransparentForInput
        vis = self.isVisible()
        self.setWindowFlags(flags)
        if vis:
            self.show()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.on_moved(self.pos())


class OverlayTab(QWidget):
    def __init__(self, board, settings, parent=None):
        super().__init__(parent)
        self.b = board
        self.settings = settings
        self.cfg = self._load()
        self.last = None
        self.hist_tq = deque(maxlen=6000)      # (t, couple N·m, iq A)
        self.hist_v = deque(maxlen=12000)      # (t, vbus)
        self.hist_brk = deque(maxlen=6000)     # (t, ibrake)
        self.hist = {}
        self._rate_n, self._rate_t, self.rate = 0, time.perf_counter(), 0.0
        self._now = time.perf_counter()
        self.win = OverlayWindow(self._moved)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(12)

        c, l = card(T("Informations affichées"))
        self.checks = {}
        grid = QGridLayout()
        for n, (key, lab, unit) in enumerate(METRICS):
            cb = QCheckBox(lab + (f"  ({unit})" if unit else ""))
            cb.setChecked(key in self.cfg["show"])
            cb.toggled.connect(self._changed)
            self.checks[key] = cb
            grid.addWidget(cb, n // 2, n % 2)
        l.addLayout(grid)
        l.addWidget(hint(T("Saturation = part du temps où le couple atteint le couple maximum du volant (ou le "
                           "courant maximum du moteur). Au-delà de quelques %, baisse la force dans le jeu ou monte "
                           "le couple maximum.")))
        left.addWidget(c)

        c, l = card(T("Apparence"))
        self.op = SettingRow(T("Opacité du fond"), 10, 100, "%")
        self.op.set_value(self.cfg["opacity"])
        self.fs = SettingRow(T("Taille du texte"), 8, 40, "pt")
        self.fs.set_value(self.cfg["font"])
        self.horiz = QCheckBox(T("Disposition horizontale"))
        self.horiz.setChecked(self.cfg["horizontal"])
        self.click = QCheckBox(T("Laisser passer les clics (overlay non déplaçable)"))
        self.click.setChecked(self.cfg["clickthrough"])
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel(T("Affichage")))
        self.mode = QComboBox()
        self.mode.addItems([T("Valeurs"), T("Courbes")])
        self.mode.setCurrentIndex(1 if self.cfg["curves"] else 0)
        mrow.addWidget(self.mode)
        mrow.addSpacing(16)
        mrow.addWidget(QLabel(T("Durée des courbes")))
        self.curve_s = QSpinBox()
        self.curve_s.setRange(2, 120)
        self.curve_s.setSuffix(" s")
        self.curve_s.setValue(int(self.cfg["curve_s"]))
        mrow.addWidget(self.curve_s)
        mrow.addStretch()
        self.mode.currentIndexChanged.connect(self._changed)
        self.curve_s.valueChanged.connect(self._changed)
        for wdg in (self.op, self.fs):
            wdg.edited.connect(self._changed)
            l.addWidget(wdg)
        for wdg in (self.horiz, self.click):
            wdg.toggled.connect(self._changed)
            l.addWidget(wdg)
        l.addLayout(mrow)
        left.addWidget(c)
        left.addStretch()
        lw = QWidget()
        lw.setLayout(left)
        left.setContentsMargins(0, 0, 8, 0)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(lw)
        root.addWidget(sc, 1)

        right = QVBoxLayout()
        c, l = card(T("Overlay"))
        row = QHBoxLayout()
        self.b_show = QPushButton(T("Afficher l'overlay"))
        self.b_show.setObjectName("primary")
        self.b_show.setCheckable(True)
        self.b_show.toggled.connect(self.toggle_window)
        self.b_reset = QPushButton(T("Replacer en haut à gauche"))
        self.b_reset.clicked.connect(self.reset_pos)
        row.addWidget(self.b_show)
        row.addWidget(self.b_reset)
        row.addStretch()
        l.addLayout(row)
        l.addWidget(hint(T("Fenêtre toujours au premier plan, déplaçable à la souris. Elle s'affiche par-dessus "
                           "les jeux en mode fenêtré ou plein écran fenêtré (borderless), pas en plein écran "
                           "exclusif.")))
        lab = QLabel(T("Aperçu"))
        lab.setObjectName("cardTitle")
        l.addWidget(lab)
        self.preview = OverlayPreview()
        prev_box = QWidget()
        prev_box.setObjectName("prevbox")
        prev_box.setAttribute(Qt.WA_StyledBackground, True)
        prev_box.setStyleSheet(f"QWidget#prevbox {{ background: {C['panel2']}; border-radius: 6px; }}")
        pl = QVBoxLayout(prev_box)
        pl.setContentsMargins(20, 20, 20, 20)
        pl.addWidget(self.preview.area)
        pl.addStretch()
        l.addWidget(prev_box, 1)
        right.addWidget(c, 1)
        root.addLayout(right, 1)

        self.b.telemetry.connect(self.on_batch)
        self._apply_style()
        t = QTimer(self)
        t.timeout.connect(self.refresh)
        t.start(50)

    # -------------------------------------------------------- config
    def _load(self):
        cfg = json.loads(json.dumps(DEFAULT))
        try:
            raw = i18n.settings().value("overlay", "")
            if raw:
                d = json.loads(raw)
                # seulement les clés connues, du même type que la valeur par défaut : une préférence abîmée ne
                # doit pas empêcher l'appli de démarrer
                cfg.update({k: v for k, v in d.items() if k in cfg and _valid(k, v)})
        except Exception:
            pass
        known = {m[0] for m in METRICS}
        cfg["show"] = [k for k in cfg["show"] if isinstance(k, str) and k in known]
        return cfg

    def _save(self):
        try:
            i18n.settings().setValue("overlay", json.dumps(self.cfg))
        except Exception:
            pass

    def _changed(self, *_):
        self.cfg["show"] = [k for k, cb in self.checks.items() if cb.isChecked()]
        self.cfg["opacity"] = self.op.value()
        self.cfg["font"] = self.fs.value()
        self.cfg["horizontal"] = self.horiz.isChecked()
        self.cfg["curves"] = self.mode.currentIndex() == 1
        self.cfg["curve_s"] = self.curve_s.value()
        old_click = self.cfg.get("clickthrough")
        self.cfg["clickthrough"] = self.click.isChecked()
        if old_click != self.cfg["clickthrough"]:
            self.win.set_clickthrough(self.cfg["clickthrough"])
        self._apply_style()
        self._save()

    def _apply_style(self):
        for p in (self.preview.panel, self.win.panel):
            p.font_pt = self.cfg["font"]
            p.horizontal = self.cfg["horizontal"]
            p.curves = self.cfg["curves"]
            p.window_s = float(self.cfg["curve_s"])
            p.bg_alpha = int(255 * self.cfg["opacity"] / 100)

    def _moved(self, pos):
        self.cfg["pos"] = [pos.x(), pos.y()]
        self._save()

    def toggle_window(self, on):
        if on:
            if self.cfg.get("pos"):
                self.win.move(QPoint(*self.cfg["pos"]))
            else:
                self.reset_pos()
            self.win.show()
            self.b_show.setText(T("Masquer l'overlay"))
        else:
            self.win.hide()
            self.b_show.setText(T("Afficher l'overlay"))

    def reset_pos(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.win.move(scr.left() + 30, scr.top() + 30)
        self._moved(self.win.pos())

    def shutdown(self):
        self.win.close()

    # -------------------------------------------------------- données
    def param(self, path):
        r = self.settings.rows.get(path)
        return r.device if (r and r.read_ok) else None

    def on_batch(self, batch):
        for tm in batch:
            self.hist_tq.append((tm.t, tm.torque, tm.iq))
            self.hist_v.append((tm.t, tm.vbus))
            self.hist_brk.append((tm.t, tm.ibrake))
        self._rate_n += len(batch)
        self.last = batch[-1]

    def _curve(self, key, v, lo, hi):
        """Mémorise la valeur et renvoie (points, lo, hi) pour la courbe, ou None en mode valeurs."""
        h = self.hist.setdefault(key, deque(maxlen=4000))
        h.append((self._now, v))
        win = self.cfg["curve_s"]
        while h and self._now - h[0][0] > win:
            h.popleft()
        if not self.cfg["curves"]:
            return None
        if lo is None:  # échelle automatique symétrique
            m = max((abs(x) for _, x in h), default=1.0) or 1.0
            lo, hi = -m * 1.1, m * 1.1
        elif hi is None:
            hi = max((x for _, x in h), default=1.0) * 1.15 or 1.0
        return (list(h), lo, hi)

    def _rows(self):
        tm = self.last
        if tm is None or not self.b.hid_ok:
            return [(T("État (connexion / moteur / erreurs)"), T("en attente de la carte…"), C["dim"], "text", None)]
        self._now = time.perf_counter()
        rows = []
        show = set(self.cfg["show"])
        rng = self.param("axis.range") or self.b.half_range * 2
        mt = self.param("axis.maxtorque")
        ilim = self.param("axis0.motor.config.current_lim")
        br = self.param("config.brake_resistance")
        t_last = self.hist_tq[-1][0] if self.hist_tq else tm.t
        pct = tm.torque / mt * 100 if mt else None
        for key, lab, unit in METRICS:
            if key not in show:
                continue
            if key == "angle":
                rows.append((lab, f"{tm.pos:+.1f} °", None, "text", self._curve(key, tm.pos, -rng / 2, rng / 2)))
            elif key == "speed":
                s = tm.vel * 360
                rows.append((lab, f"{s:+.0f} °/s", C["bad"] if self.b.guard_armed and abs(s) > self.b.guard_limit
                             else None, "text", self._curve(key, s, None, None)))
            elif key == "torque":
                lim = mt or 5.0
                rows.append((lab, f"{tm.torque:+.2f} N·m", C["bad"] if pct is not None and abs(pct) >= 98 else
                             (C["blue"] if self.cfg["curves"] else None), "text",
                             self._curve(key, tm.torque, -lim, lim)))
            elif key == "torque_pct":
                rows.append((lab, f"{pct:+.0f} %" if pct is not None else "—",
                             C["bad"] if pct is not None and abs(pct) >= 98 else None, "text",
                             self._curve(key, pct or 0.0, -100, 100)))
            elif key == "torque_bar":
                rows.append(("", "", None, "bar", pct or 0.0))
            elif key == "torque_peak":
                pk = max((abs(q) for (ts, q, _i) in self.hist_tq if t_last - ts <= 3.0), default=0.0)
                rows.append((lab, f"{pk:.2f} N·m", C["warn"] if mt and pk >= 0.98 * mt else None, "text",
                             self._curve(key, pk, 0, mt or None)))
            elif key == "clipping":
                win = [(abs(q), abs(i)) for (ts, q, i) in self.hist_tq if t_last - ts <= 5.0]
                sat = sum(1 for q, i in win if (mt and q >= 0.98 * mt) or (ilim and i >= 0.98 * ilim))
                c = 100.0 * sat / len(win) if win else 0.0
                rows.append((lab, f"{c:.0f} %", C["bad"] if c > 5 else C["ok"], "text", self._curve(key, c, 0, 100)))
            elif key == "iq":
                rows.append((lab, f"{tm.iq:+.1f} A", C["bad"] if ilim and abs(tm.iq) >= 0.98 * ilim else None,
                             "text", self._curve(key, tm.iq, -(ilim or 10), ilim or 10)))
            elif key == "vbus":
                ov = self.param("config.dc_bus_overvoltage_trip_level")
                uv = self.param("config.dc_bus_undervoltage_trip_level")
                col = C["bad"] if (ov and tm.vbus > ov - 1.5) or (uv and tm.vbus < uv + 1.0) else None
                rows.append((lab, f"{tm.vbus:.1f} V", col, "text",
                             self._curve(key, tm.vbus, (uv or 0) * 0.95, (ov or 60) * 1.02)))
            elif key == "vsag":
                vm = min((v for (ts, v) in self.hist_v if t_last - ts <= 10.0), default=tm.vbus)
                uv = self.param("config.dc_bus_undervoltage_trip_level")
                rows.append((lab, f"{vm:.1f} V", C["warn"] if uv and vm < uv + 2 else None, "text",
                             self._curve(key, vm, (uv or 0) * 0.95, None)))
            elif key == "ibus":
                rows.append((lab, f"{tm.ibus:+.2f} A", None, "text", self._curve(key, tm.ibus, None, None)))
            elif key == "pin":
                p = tm.vbus * tm.ibus
                rows.append((lab, f"{p:+.0f} W", None, "text", self._curve(key, p, None, None)))
            elif key == "ibrake":
                rows.append((lab, f"{tm.ibrake:.2f} A", None, "text", self._curve(key, tm.ibrake, 0, None)))
            elif key == "pbrake":
                win = [i for (ts, i) in self.hist_brk if t_last - ts <= 5.0]
                p = (sum(i * i for i in win) / len(win) * br) if (win and br) else None
                rows.append((lab, f"{p:.1f} W" if p is not None else "—",
                             C["warn"] if p is not None and p > 25 else None, "text",
                             self._curve(key, p or 0.0, 0, None)))
            elif key == "fet":
                v = tm.fet_c
                rows.append((lab, "—" if v is None else f"{v:.0f} °C",
                             C["bad"] if (v or 0) >= 90 else C["warn"] if (v or 0) >= 70 else None, "text",
                             self._curve(key, v or 0.0, 0, None)))
            elif key == "range_used":
                ru = min(100.0, abs(tm.pos) / (rng / 2) * 100) if rng else 0.0
                rows.append((lab, f"{ru:.0f} %", None, "text", self._curve(key, ru, 0, 100)))
            elif key == "fps":
                rows.append((lab, f"{self.rate:.0f}", None, "text", self._curve(key, self.rate, 0, None)))
            elif key == "status":
                if self.b.estop:
                    rows.append((lab, "STOP", C["bad"], "text", None))
                elif tm.any_error:
                    rows.append((lab, T("ERREUR"), C["bad"], "text", None))
                elif tm.state == P.CLOSED_LOOP:
                    rows.append((lab, T("actif"), C["ok"], "text", None))
                else:
                    rows.append((lab, T("au repos") if tm.state == P.IDLE else P.STATES.get(tm.state, ("?", "?"))[0],
                                 C["warn"], "text", None))
        return rows

    def refresh(self):
        now = time.perf_counter()
        if now - self._rate_t >= 1.0:
            self.rate = self._rate_n / (now - self._rate_t)
            self._rate_n, self._rate_t = 0, now
        if not (self.isVisible() or self.win.isVisible()):
            return
        rows = self._rows()
        if self.isVisible():
            self.preview.set_rows(rows)
        if self.win.isVisible():
            self.win.panel.set_rows(rows)
            hint_ = self.win.panel.sizeHint()
            if self.win.size() != hint_:
                self.win.resize(hint_)
