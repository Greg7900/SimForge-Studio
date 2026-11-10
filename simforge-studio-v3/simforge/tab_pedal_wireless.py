"""Page Pédales › Sans fil : appairage ESP-NOW des pédales et du récepteur, comme « System › Wireless » du plugin
SimHub de ChrGri. Chaque appareil garde en mémoire la table des adresses (embrayage, frein, accélérateur, récepteur)
et le canal Wi-Fi ; elle s'écrit par le port série : celui de chaque pédale, et la prise UART du récepteur."""
from __future__ import annotations

import threading

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
                               QSpinBox, QPlainTextEdit, QMessageBox)

from . import ped_protocol as PP
from .i18n import T
from .theme import C
from .widgets import card, hint


def merge_table(pedals: dict, bridge: dict | None):
    """Table à enregistrer partout. pedals : {port: table reçue de la pédale} ; bridge : table reçue du récepteur.
    Les appareils branchés donnent leur propre adresse ; les cases des pédales absentes gardent ce qui était déjà
    enregistré (on peut appairer une pédale à la fois). Renvoie (4 adresses, erreur)."""
    known = [t for t in ([bridge] if bridge else []) + list(pedals.values()) if t]
    macs = [bytes(6)] * 4
    for t in reversed(known):                       # la table du récepteur l'emporte
        macs = [m if any(m) else old for m, old in zip(t["macs"], macs)]
    if bridge:
        macs[PP.N_BRIDGE] = bridge["own"]
    seen = {}
    for port, t in pedals.items():
        if not t:
            continue
        role = t["node"]
        if role not in (0, 1, 2):
            return None, T("{p} n'a pas de rôle : choisis-le dans Réglages (Rôle de la pédale) et enregistre.").format(
                p=port)
        if role in seen:
            return None, T("{a} et {b} ont le même rôle ({r}) : change le rôle de l'une dans Réglages.").format(
                a=seen[role], b=port, r=PP.PEDAL_NAMES[role])
        seen[role] = port
        macs = [bytes(6) if (m == t["own"] and i != role) else m for i, m in enumerate(macs)]   # ancienne case
        macs[role] = t["own"]
    if not any(macs[PP.N_BRIDGE]):
        return None, T("Adresse du récepteur inconnue : branche sa prise UART, choisis son port et clique Détecter.")
    if not seen:
        return None, T("Aucune pédale connectée.")
    return macs, ""


class WirelessTab(QWidget):
    _bridge_done = Signal(object, str, bool)        # (table ou None, erreur, était-ce un enregistrement)
    _boot_done = Signal(str, str)

    def __init__(self, mgr, parent=None):
        super().__init__(parent)
        self.m = mgr
        self.ped = {}                               # port → table reçue
        self.bridge = None
        self.busy = False
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 8)
        root.setSpacing(12)

        c, l = card(T("Appairage sans fil (ESP-NOW)"))
        l.addWidget(hint(T(
            "À faire une fois. 1. Branche chaque pédale en USB (elles doivent apparaître dans Réglages, chacune avec "
            "son rôle). 2. Branche le récepteur par sa prise UART (puce CH343) et choisis son port. 3. Détecter, "
            "puis Appairer. Ensuite, branche le récepteur par sa prise USB : c'est lui la manette pour les jeux, et "
            "les câbles des pédales peuvent être retirés. Ferme SimHub pendant l'opération.")))
        r = QHBoxLayout()
        r.addWidget(QLabel(T("Port du récepteur (UART)")))
        self.port_cb = QComboBox()
        self.port_cb.setMinimumWidth(260)
        r.addWidget(self.port_cb)
        b = QPushButton(T("Actualiser"))
        b.clicked.connect(self._ports)
        r.addWidget(b)
        r.addSpacing(20)
        r.addWidget(QLabel(T("Canal Wi-Fi")))
        self.ch = QSpinBox()
        self.ch.setRange(1, 13)
        self.ch.setValue(11)
        self.ch.setToolTip(T("Le même pour tous. Change-le seulement si la liaison décroche (Wi-Fi voisin)."))
        r.addWidget(self.ch)
        r.addStretch()
        l.addLayout(r)

        g = QGridLayout()
        g.setHorizontalSpacing(24)
        for k, t in enumerate((T("Appareil"), T("Adresse"), T("Branché sur"), T("Enregistré dans le récepteur"))):
            h = QLabel(t)
            h.setObjectName("hint")
            g.addWidget(h, 0, k)
        self.rows = []
        for i in range(4):
            name = QLabel(T("Récepteur") if i == PP.N_BRIDGE else PP.PEDAL_NAMES[i])
            cells = [QLabel("—"), QLabel("—"), QLabel("—")]
            cells[0].setObjectName("mono")
            cells[2].setObjectName("mono")
            g.addWidget(name, i + 1, 0)
            for k, w in enumerate(cells):
                g.addWidget(w, i + 1, k + 1)
            self.rows.append(cells)
        g.setColumnStretch(4, 1)
        l.addLayout(g)

        r = QHBoxLayout()
        self.b_detect = QPushButton(T("Détecter"))
        self.b_detect.clicked.connect(self.detect)
        self.b_pair = QPushButton(T("Appairer"))
        self.b_pair.setObjectName("primary")
        self.b_pair.clicked.connect(self.pair)
        self.b_boot = QPushButton(T("Journal de démarrage"))
        self.b_boot.setToolTip(T("Redémarre la carte branchée sur ce port et affiche ce qu'elle écrit en démarrant : "
                                 "sert à comprendre une carte qui ne répond pas (firmware qui ne démarre pas)."))
        self.b_boot.clicked.connect(self.boot_log)
        r.addWidget(self.b_detect)
        r.addWidget(self.b_pair)
        r.addStretch()
        r.addWidget(self.b_boot)
        l.addLayout(r)
        self.res = QLabel("")
        self.res.setWordWrap(True)
        l.addWidget(self.res)
        root.addWidget(c)

        self.log = QPlainTextEdit()
        self.log.setObjectName("console")
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)

        self.m.mac_read.connect(self._on_ped)
        self.m.text.connect(self._on_text)
        self.m.changed.connect(self._ports)
        self._bridge_done.connect(self._on_bridge)
        self._boot_done.connect(self._on_boot)
        self._ports()

    def showEvent(self, e):
        self._ports()
        super().showEvent(e)

    # ------------------------------------------------------------ affichage
    def _ports(self, *_):
        cur = self.port_cb.currentData()
        self.port_cb.clear()
        for p in self.m.bridge_ports():
            self.port_cb.addItem(p, p)
        i = self.port_cb.findData(cur)
        if i >= 0:
            self.port_cb.setCurrentIndex(i)
        live = {p.port for p in self.m.pedals()}
        self.ped = {p: t for p, t in self.ped.items() if p in live}
        self._show()

    def _show(self):
        own = {t["node"]: (t["own"], port) for port, t in self.ped.items() if t}
        if self.bridge:
            own[PP.N_BRIDGE] = (self.bridge["own"], self.port_cb.currentData() or "")
        stored = self.bridge["macs"] if self.bridge else [None] * 4
        for i, (mac, port, st) in enumerate(self.rows):
            m, p = own.get(i, (None, ""))
            mac.setText(PP.mac_text(m))
            port.setText(p or "—")
            st.setText(PP.mac_text(stored[i]) if self.bridge else "—")
            ok = self.bridge is not None and m is not None and stored[i] == m
            st.setStyleSheet(f"color: {C['ok']};" if ok else "")
        if self.bridge and not self.busy:
            self.ch.setValue(self.bridge["channel"] if 1 <= self.bridge["channel"] <= 13 else 11)

    def _say(self, text, level=""):
        self.res.setText(text)
        self.res.setStyleSheet(f"color: {C[level]};" if level else "")
        self.log.appendPlainText(text)

    def _on_text(self, port, line):
        if "[MAC]" in line:
            self.log.appendPlainText(f"{port} : {line}")

    def _on_ped(self, port, table):
        self.ped[port] = table
        self._show()

    # ------------------------------------------------------------ actions
    def _bridge(self, frame, store):
        port = self.port_cb.currentData()
        if not port:
            self._bridge_done.emit(None, T("aucun port choisi"), store)
            return
        self.busy = True
        for b in (self.b_detect, self.b_pair, self.b_boot):
            b.setEnabled(False)

        def work():
            got, err = self.m.bridge_exchange(port, frame)
            self._bridge_done.emit(got, err, store)
        threading.Thread(target=work, daemon=True).start()

    def boot_log(self):
        port = self.port_cb.currentData()
        if not port or self.busy:
            return
        self.busy = True
        for b in (self.b_detect, self.b_pair, self.b_boot):
            b.setEnabled(False)
        self._say(T("Redémarrage de la carte sur {p}…").format(p=port))
        threading.Thread(target=lambda: self._boot_done.emit(*self.m.boot_log(port)), daemon=True).start()

    def _on_boot(self, text, err):
        self.busy = False
        for b in (self.b_detect, self.b_pair, self.b_boot):
            b.setEnabled(True)
        if err:
            self._say(T("Lecture impossible : {e}").format(e=err), "bad")
            return
        self.log.appendPlainText("-" * 60 + "\n" + (text or T("(rien reçu)")) + "\n" + "-" * 60)
        self.res.setText(T("Journal de démarrage affiché ci-dessous."))
        self.res.setStyleSheet("")

    def detect(self):
        self.ped = {}
        for p in self.m.pedals():
            self.m.send_mac(p.port)
        self._say(T("Détection…"))
        self._bridge(PP.build_mac(), False)

    def _on_bridge(self, got, err, store):
        self.busy = False
        for b in (self.b_detect, self.b_pair, self.b_boot):
            b.setEnabled(True)
        if got is not None:
            self.bridge = got
        self._show()
        if store:
            if got is None:
                self._say(T("✖ Le récepteur n'a pas confirmé ({e}). Les pédales ont reçu la table ; rebranche la "
                            "prise UART du récepteur et recommence.").format(e=err), "bad")
            else:
                # relecture des pédales pour confirmer ce qu'elles ont retenu
                QTimer.singleShot(600, lambda: [self.m.send_mac(p.port) for p in self.m.pedals()])
                self._say(T("✔ Appairage enregistré (canal {c}). Branche maintenant le récepteur par sa prise USB ; "
                            "les câbles des pédales peuvent être retirés.").format(c=got["channel"]), "ok")
            return
        if got is None:
            self._say(T("Récepteur introuvable sur {p} ({e}) : branche sa prise UART (pas la prise USB), ferme "
                        "SimHub, et vérifie qu'il est flashé avec le firmware « Récepteur sans fil ».").format(
                p=self.port_cb.currentData() or "—", e=err), "warn")
        else:
            self._say(T("Récepteur trouvé : {m}.").format(m=PP.mac_text(got["own"])), "ok")

    def pair(self):
        macs, err = merge_table(self.ped, self.bridge)
        if err:
            QMessageBox.warning(self, T("Appairer"), err)
            return
        if QMessageBox.question(self, T("Appairer"), T(
                "Enregistrer cette table dans le récepteur et dans {n} pédale(s), sur le canal {c} ?").format(
                n=len(self.ped), c=self.ch.value())) != QMessageBox.Yes:
            return
        ch = self.ch.value()
        for port in self.ped:
            self.m.send_mac(port, macs, ch, True)
        self._say(T("Enregistrement…"))
        self._bridge(PP.build_mac(macs, ch, True), True)
