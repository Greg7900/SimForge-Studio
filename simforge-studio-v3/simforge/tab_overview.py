"""Page Vue d'ensemble : volant et pédales d'un coup d'œil, avec les liens vers la page qui règle chaque élément."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton

from . import ow_protocol as P
from . import ped_protocol as PP
from .i18n import T
from .theme import C
from .widgets import card, hint, AxisBar, CenterBar, Led


class _PedalBox(QWidget):
    def __init__(self):
        super().__init__()
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        self.led = Led(C["bad"], 10)
        self.title = QLabel("")
        self.title.setStyleSheet("font-weight: 700;")
        h = QHBoxLayout()
        h.addWidget(self.led)
        h.addWidget(self.title, 1)
        g.addLayout(h, 0, 0, 1, 3)
        self.bars = {}
        for i, (k, lab, col) in enumerate((("pos", T("Course"), C["accent"]), ("force", T("Force"), C["blue"]),
                                           ("joy", T("Axe envoyé au jeu"), C["ok"]))):
            g.addWidget(QLabel(lab), i + 1, 0)
            b = AxisBar(color=col)
            b.set(0)
            g.addWidget(b, i + 1, 1)
            v = QLabel("—")
            v.setObjectName("midValue")
            v.setMinimumWidth(90)
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            g.addWidget(v, i + 1, 2)
            self.bars[k] = (b, v)
        g.setColumnStretch(1, 1)
        self.err = QLabel("")
        self.err.setWordWrap(True)
        g.addWidget(self.err, 4, 0, 1, 3)


class OverviewTab(QWidget):
    goto = Signal(str)          # clé de page

    def __init__(self, board, pedals, parent=None):
        super().__init__(parent)
        self.b, self.m = board, pedals
        self.boxes: dict[str, _PedalBox] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)
        row = QHBoxLayout()
        row.setSpacing(12)

        # ---------------------------------------------- volant
        c, l = card(T("Volant"))
        self.w_state = QLabel(T("Carte non connectée"))
        self.w_state.setStyleSheet("font-weight: 700;")
        l.addWidget(self.w_state)
        g = QGridLayout()
        self.w = {}
        for i, (k, lab) in enumerate((("pos", T("Angle")), ("torque", T("Couple")), ("vbus", T("Batterie")),
                                      ("temp", T("Température carte")))):
            g.addWidget(QLabel(lab), i, 0)
            v = QLabel("—")
            v.setObjectName("midValue")
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            v.setMinimumWidth(110)
            g.addWidget(v, i, 2)
            self.w[k] = v
        self.w_bar = CenterBar()
        g.addWidget(self.w_bar, 0, 1)
        g.setColumnStretch(1, 1)
        l.addLayout(g)
        self.w_err = QLabel("")
        self.w_err.setWordWrap(True)
        l.addWidget(self.w_err)
        h = QHBoxLayout()
        for key, txt in (("w_settings", T("Réglages du volant")), ("w_monitor", T("Moniteur"))):
            b = QPushButton(txt)
            b.clicked.connect(lambda _=False, k=key: self.goto.emit(k))
            h.addWidget(b)
        h.addStretch()
        l.addLayout(h)
        l.addStretch()
        row.addWidget(c, 1)

        # ---------------------------------------------- pédales
        c, l = card(T("Pédales"))
        self.p_none = hint(T("Aucune pédale détectée. Branche chaque pédale par son port USB « UART » (puce "
                             "CH343/CP210x) et ferme SimHub, qui garde les ports ouverts."))
        l.addWidget(self.p_none)
        self.p_lay = QVBoxLayout()
        self.p_lay.setSpacing(14)
        l.addLayout(self.p_lay)
        h = QHBoxLayout()
        b = QPushButton(T("Réglages des pédales"))
        b.clicked.connect(lambda: self.goto.emit("p_settings"))
        h.addWidget(b)
        b = QPushButton(T("Firmware des pédales"))
        b.clicked.connect(lambda: self.goto.emit("p_fw"))
        h.addWidget(b)
        h.addStretch()
        l.addLayout(h)
        l.addStretch()
        row.addWidget(c, 1)
        root.addLayout(row, 1)
        root.addWidget(hint(T("Pour vérifier ce que voit le jeu (volant + pédales), utilise Outils › Joy tester.")))

        board.telemetry.connect(self._tm)
        board.link_changed.connect(self._link)
        pedals.changed.connect(self._pedals)
        pedals.states.connect(self._pstates)
        self._pedals()
        t = QTimer(self)
        t.timeout.connect(self._slow)
        t.start(500)
        self._last = None

    # ------------------------------------------------------------ volant
    def _link(self, _info):
        if not self.b.serial_ok and not self.b.hid_ok:
            self.w_state.setText(T("Carte non connectée"))
            self.w_state.setStyleSheet(f"font-weight: 700; color: {C['bad']};")
            for v in self.w.values():
                v.setText("—")

    def _tm(self, batch):
        self._last = batch[-1]

    def _slow(self):
        if not self.isVisible():
            return
        tm = self._last
        if tm is None or not self.b.hid_ok:
            return
        self.w["pos"].setText(f"{tm.pos:+.1f} °")
        hr = getattr(self.b, "half_range", None) or 450.0
        self.w_bar.set(tm.pos / hr * 100)
        self.w["torque"].setText(f"{tm.torque:+.2f} N·m")
        self.w["vbus"].setText(f"{tm.vbus:.1f} V")
        self.w["temp"].setText(f"{tm.fet_c:.0f} °C" if tm.fet_c is not None else T("pas de capteur"))
        if tm.any_error:
            txt, col = T("Erreur"), C["bad"]
            self.w_err.setText(", ".join(n for _g, n, _d in P.errors_of(tm)))
            self.w_err.setStyleSheet(f"color: {C['bad']};")
        else:
            self.w_err.setText("")
            if tm.state == P.CLOSED_LOOP:
                txt, col = T("Moteur actif"), C["ok"]
            elif tm.state in P.CALIBRATING:
                txt, col = T("Calage en cours"), C["blue"]
            else:
                txt, col = T("Moteur au repos"), C["warn"]
        self.w_state.setText(txt)
        self.w_state.setStyleSheet(f"font-weight: 700; color: {col};")
        for port, box in self.boxes.items():
            info = self.m.info(port)
            if info:
                box.title.setText(info.name + (f"  ·  fw {info.fw}" if info.fw else ""))
                box.led.set(C["bad"] if info.incompatible else C["ok"])

    # ------------------------------------------------------------ pédales
    def _pedals(self):
        ports = [p.port for p in self.m.pedals()]
        for port in list(self.boxes):
            if port not in ports:
                self.boxes.pop(port).deleteLater()
        for p in self.m.pedals():
            if p.port not in self.boxes:
                box = _PedalBox()
                self.boxes[p.port] = box
                self.p_lay.addWidget(box)
            box = self.boxes[p.port]
            box.title.setText(p.name)
            box.led.set(C["bad"] if p.incompatible else C["ok"])
            if p.incompatible:
                box.err.setText(T("Firmware incompatible : flashe-le dans Pédales › Firmware."))
                box.err.setStyleSheet(f"color: {C['bad']};")
        self.p_none.setVisible(not self.boxes)

    def _pstates(self, batch):
        if not self.isVisible():
            return
        last = {}
        for port, _t, st in batch:
            last[port] = st
        for port, st in last.items():
            box = self.boxes.get(port)
            if not box:
                continue
            info = self.m.info(port)
            cfg = info.config if info else None
            pos = st["pedalPosition_u16"] / 65535
            frc = st["pedalForce_u16"] / 65535
            joy = st["joystickOutput_u16"] / 65535
            box.bars["pos"][0].set(pos)
            box.bars["pos"][1].setText(f"{pos * 100:.0f} %")
            box.bars["force"][0].set(frc)
            if cfg:
                kg = cfg["preloadForce_fl32"] + frc * (cfg["maxForce_fl32"] - cfg["preloadForce_fl32"])
                box.bars["force"][1].setText(f"{kg:.1f} kg")
            else:
                box.bars["force"][1].setText(f"{frc * 100:.0f} %")
            box.bars["joy"][0].set(joy)
            box.bars["joy"][1].setText(f"{joy * 100:.0f} %")
            e = st.get("errorCode_u8", 0)
            if e:
                box.err.setText(T("Erreur {c} : {d}").format(c=e, d=PP.ERROR_CODES.get(e, T("code inconnu"))))
                box.err.setStyleSheet(f"color: {C['bad']};")
            elif not (info and info.incompatible):
                box.err.setText("")
