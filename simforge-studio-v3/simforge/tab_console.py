"""Onglet Console : terminal sur le port série de la carte (commandes ODrive ASCII et OpenFFBoard)."""
from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QPushButton, QPlainTextEdit, QLabel,
                               QListWidget, QListWidgetItem, QMessageBox)

from .i18n import T
from .theme import C
from .widgets import card, hint

# commande, description
COMMANDS = [
    ("r vbus_voltage", T("Tension du bus")),
    ("r ibus", T("Courant du bus")),
    ("r error", T("Erreur système (tension, courant…)")),
    ("r axis0.current_state", T("État de l'axe (1 repos, 8 boucle fermée)")),
    ("r axis0.error", T("Erreur de l'axe")),
    ("r axis0.motor.error", T("Erreur moteur")),
    ("r axis0.encoder.error", T("Erreur codeur")),
    ("r axis0.controller.error", T("Erreur contrôleur")),
    ("r axis0.encoder.shadow_count", T("Compteur du codeur")),
    ("r axis0.encoder.is_ready", T("Codeur calé ?")),
    ("r axis0.motor.config.phase_resistance", T("Résistance de phase mesurée")),
    ("r axis0.motor.config.phase_inductance", T("Inductance de phase mesurée")),
    ("w axis0.requested_state 1", T("Moteur au repos (libre)")),
    ("w axis0.requested_state 4", T("Calibration moteur (le moteur siffle)")),
    ("w axis0.requested_state 7", T("Calage du codeur (le moteur tourne ~1 tour)")),
    ("w axis0.requested_state 8", T("Boucle fermée (moteur actif)")),
    ("sc", T("Effacer les erreurs")),
    ("ss", T("Mémoriser la config ODrive et redémarrer (moteur au repos)")),
    ("sr", T("Redémarrer la carte")),
    ("sys.save!", T("Mémoriser les réglages volant/effets")),
    ("sys.fxtest?", T("Résumé FFB : actif, position, vitesse, couple, effets")),
    ("axis.zeroenc!", T("Prendre la position actuelle comme centre")),
    ("sys.vbusdiv?", T("Rapport du pont diviseur de tension")),
    ("sys.savestat?", T("Résultat de la dernière mémorisation")),
    ("sys.eedump?", T("Diagnostic de la mémoire des réglages volant")),
    ("I", T("Pics de courant et de tension depuis le démarrage")),
    ("sys.temp?", T("Température des transistors")),
    ("sys.uptime?", T("Temps depuis le démarrage")),
    ("sys.help?", T("Liste des commandes OpenFFBoard")),
]
DANGER = {"se": T("efface toute la configuration ODrive"), "sd": T("passe la carte en mode DFU"),
          "sys.eeformat!": T("efface la mémoire des réglages volant")}


class ConsoleTab(QWidget):
    def __init__(self, board, parent=None):
        super().__init__(parent)
        self.b = board
        self.hist, self.hpos = [], 0
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        c, l = card(T("Console série"))
        l.addWidget(hint(T("Envoie des commandes à la carte. ODrive : « r chemin » lit, « w chemin valeur » écrit "
                           "(muet si accepté). OpenFFBoard : « classe.cmd? » lit, « = » écrit, « ! » exécute. "
                           "Les modifications ne sont pas mémorisées sans « ss » ou « sys.save! ».")))
        self.out = QPlainTextEdit()
        self.out.setObjectName("console")
        self.out.setReadOnly(True)
        self.out.setMaximumBlockCount(5000)
        l.addWidget(self.out, 1)
        row = QHBoxLayout()
        p = QLabel("›")
        p.setStyleSheet(f"color: {C['accent']}; font-size: 13pt;")
        row.addWidget(p)
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(T("Commande (Entrée pour envoyer, ↑/↓ historique)…"))
        self.inp.returnPressed.connect(self.send)
        self.inp.installEventFilter(self)
        row.addWidget(self.inp, 1)
        b = QPushButton(T("Envoyer"))
        b.setObjectName("primary")
        b.clicked.connect(self.send)
        row.addWidget(b)
        b2 = QPushButton(T("Effacer"))
        b2.clicked.connect(self.out.clear)
        row.addWidget(b2)
        l.addLayout(row)
        root.addWidget(c, 3)

        c, l = card(T("Commandes utiles"))
        l.addWidget(hint(T("Double-clic pour copier dans la ligne de commande.")))
        self.list = QListWidget()
        for cmd, desc in COMMANDS:
            it = QListWidgetItem(f"{cmd}\n    {desc}")
            it.setData(Qt.UserRole, cmd)
            self.list.addItem(it)
        self.list.itemDoubleClicked.connect(lambda it: (self.inp.setText(it.data(Qt.UserRole)), self.inp.setFocus()))
        l.addWidget(self.list, 1)
        root.addWidget(c, 2)

        self.b.console.connect(self.on_rx)
        self.b.link_changed.connect(self.on_link)

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if obj is self.inp and ev.type() == QEvent.KeyPress and self.hist:
            if ev.key() == Qt.Key_Up:
                self.hpos = max(0, self.hpos - 1)
                self.inp.setText(self.hist[self.hpos])
                return True
            if ev.key() == Qt.Key_Down:
                self.hpos = min(len(self.hist), self.hpos + 1)
                self.inp.setText(self.hist[self.hpos] if self.hpos < len(self.hist) else "")
                return True
        return super().eventFilter(obj, ev)

    def _append(self, text, color):
        for line in text.splitlines() or [""]:
            esc = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            self.out.appendHtml(f'<span style="color:{C["dim"]}">{time.strftime("%H:%M:%S")}</span> '
                                f'<span style="color:{color}">{esc}</span>')

    def send(self):
        line = self.inp.text().strip()
        if not line:
            return
        if line in DANGER and QMessageBox.question(
                self, T("Commande sensible"), T("« {c} » {d}. Continuer ?").format(c=line, d=DANGER[line])) \
                != QMessageBox.Yes:
            return
        self.hist.append(line)
        self.hpos = len(self.hist)
        self.inp.clear()
        self._append("› " + line, C["accent"])
        if not self.b.serial_ok:
            self._append(T("Port série non connecté."), C["bad"])
            return
        if line.startswith("w axis0.requested_state") and self.b.estop and not line.endswith(" 1"):
            self._append(T("STOP enclenché : réarme-le avant d'activer le moteur."), C["bad"])
            return
        self.b.raw(line)

    def on_rx(self, kind, text):
        self._append(text, C["bad"] if kind == "err" else C["text"])

    def on_link(self, info):
        if info.get("serial") is True:
            self._append(T("Port série {p} ouvert.").format(p=info.get("port")), C["ok"])
        elif info.get("serial") is False:
            self._append(T("Port série fermé ({w}).").format(w=info.get("why", "")), C["warn"])
