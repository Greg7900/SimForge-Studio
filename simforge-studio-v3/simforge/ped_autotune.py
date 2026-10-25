"""Auto-test (bêta) des pédales : cherche le filtre et l'amortissement les plus réactifs sans oscillation.

Déroulé : bruit du capteur pied posé, puis filtre IMM adaptatif et paliers de « Vitesse du filtre » de 255 à 64 ;
à chaque palier l'utilisateur appuie et relâche doucement et l'on compte les trames où le firmware signale une
oscillation (admittance_isOscillating de l'état détaillé). Si tous les paliers oscillent, on monte l'amortissement.
Tout est envoyé avec « Appliquer » (rien n'est mémorisé) à partir de la configuration lue au départ : les
modifications en attente de la page ne partent pas. « Arrêter » ou « Revenir » renvoie la configuration de départ.
"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
                               QPlainTextEdit, QMessageBox)

from . import ped_protocol as PP
from .ped_device import new_ext_acc
from .i18n import T
from .theme import C
from .widgets import hint

SPEEDS = (255, 180, 128, 90, 64)        # « Vitesse du filtre », de la plus réactive à la plus calme
DAMPINGS = (150, 200, 250)              # « Amortissement virtuel » (%) essayés si tous les paliers oscillent
OSC_MAX = 0.002                         # part de trames en oscillation tolérée (bruit de détection)
MIN_TRAVEL = 15.0                       # course parcourue (%) pour qu'un palier soit valable
IMM = 4


class AutoTune(QWidget):
    REST_S, SETTLE_S, MOVE_S = 5.0, 2.0, 10.0       # durées des étapes (s)

    def __init__(self, page):
        super().__init__()
        self.p = page                   # PedalsTab
        self.orig = None                # configuration de la pédale au lancement
        self.steps = []
        self.cur = None
        self.results = []
        self.final = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        warn = hint(T(
            "Bêta. Cherche le réglage de filtre le plus réactif qui ne fait pas vibrer la pédale : filtre IMM "
            "adaptatif, puis vitesse du filtre de 255 à 64, puis amortissement si besoin. Environ 1 à 2 min. "
            "Rien n'est enregistré dans la pédale pendant le test ; tes modifications en attente ne sont pas "
            "envoyées. Garde le pied sur la pédale et suis les consignes ; « Arrêter » remet tes réglages."))
        warn.setStyleSheet(f"color: {C['warn']};")
        lay.addWidget(warn)
        hb = QHBoxLayout()
        self.b_start = QPushButton(T("Lancer l'auto-test"))
        self.b_start.setObjectName("primary")
        self.b_start.clicked.connect(self.start)
        self.b_stop = QPushButton(T("Arrêter"))
        self.b_stop.setObjectName("danger")
        self.b_stop.clicked.connect(lambda: self.stop(T("Auto-test arrêté : réglages de départ remis.")))
        hb.addWidget(self.b_start)
        hb.addWidget(self.b_stop)
        hb.addStretch()
        lay.addLayout(hb)
        self.step_lbl = QLabel("")
        self.step_lbl.setObjectName("midValue")
        self.step_lbl.setWordWrap(True)
        lay.addWidget(self.step_lbl)
        self.todo = QLabel("")
        self.todo.setWordWrap(True)
        self.todo.setStyleSheet(f"font-size: 12pt; color: {C['accent']};")
        lay.addWidget(self.todo)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setMaximumHeight(8)
        lay.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setObjectName("console")
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(150)
        lay.addWidget(self.log)
        hb = QHBoxLayout()
        self.b_keep = QPushButton(T("Enregistrer ce réglage dans la pédale"))
        self.b_keep.setObjectName("primary")
        self.b_keep.clicked.connect(self.keep)
        self.b_back = QPushButton(T("Revenir aux réglages d'avant"))
        self.b_back.clicked.connect(self.back)
        hb.addWidget(self.b_keep)
        hb.addWidget(self.b_back)
        hb.addStretch()
        lay.addLayout(hb)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.page_states = page.m.states
        self.page_states.connect(self._on_states)
        self.pos = []
        self._buttons()

    # ------------------------------------------------------------ boutons
    def _buttons(self):
        running = self.cur is not None
        self.b_start.setEnabled(not running and self.p.port is not None and self.p.cfg is not None)
        self.b_stop.setEnabled(running)
        self.b_keep.setVisible(self.final is not None and not running)
        self.b_back.setVisible(self.final is not None and not running)

    def _send(self, cfg):
        err = self.p.m.send_config(self.port, cfg, False)
        if err:
            self.stop(T("Réglage refusé, auto-test arrêté : {e}").format(e=err))
        return not err

    def _cfg(self, **kw):
        c = dict(self.orig)
        c["debugFlags0_u8"] = self.orig["debugFlags0_u8"] | PP.DBG_EXT_STATE | PP.DBG_EXT_DECIMATED
        c.update(kw)
        return c

    # ------------------------------------------------------------ déroulé
    def start(self):
        if self.p.port is None or self.p.cfg is None:
            return
        self.port = self.p.port
        self.orig = dict(self.p.cfg)
        self.results, self.final = [], None
        self.log.clear()
        damping0 = max(self.orig["virtualPedalDampingInPercent_u8"], 100)
        self.steps = [("rest", {})] + [("speed", {"kfModelOrder_u8": IMM, "kfModelNoise_u8": s,
                                                   "virtualPedalDampingInPercent_u8": damping0}) for s in SPEEDS]
        self.damping0 = damping0
        self._say(T("Auto-test lancé sur {p}.").format(p=self.port))
        self._next()

    def _next(self):
        if not self.steps:
            self._finish()
            return
        kind, kw = self.steps.pop(0)
        if kind == "speed" and any(r[3] for r in self.results if r[0] == "speed"):
            self._next()                # un palier sans oscillation a déjà été trouvé : inutile d'aller plus bas
            return
        self.cur = {"kind": kind, "kw": kw, "t0": time.monotonic(), "measuring": False, "tries":
                    self.cur["tries"] if self.cur and self.cur.get("retry") else 0}
        if not self._send(self._cfg(**kw)):
            return
        if kind == "rest":
            self.step_lbl.setText(T("Étape 1 : bruit du capteur"))
            self.todo.setText(T("Pose le pied sur la pédale SANS appuyer, et ne bouge plus."))
        else:
            n = SPEEDS.index(kw["kfModelNoise_u8"]) + 1 if kw["kfModelNoise_u8"] in SPEEDS else 0
            self.step_lbl.setText(T("Vitesse du filtre {s}, amortissement {d} %").format(
                s=kw["kfModelNoise_u8"], d=kw["virtualPedalDampingInPercent_u8"]) + (f"  ({n}/{len(SPEEDS)})" if n else ""))
            self.todo.setText(T("Attends… puis appuie et relâche doucement, plusieurs fois, comme quand ça vibrait."))
        self.timer.start(50)
        self._buttons()

    def _on_states(self, batch):
        if self.cur and self.cur["measuring"]:
            for port, _t, st in batch:
                if port == self.port:
                    self.pos.append(st["pedalPosition_u16"] / 65535 * 100)

    def _tick(self):
        c = self.cur
        info = self.p.m.info(self.port)
        if c is None:
            return
        if info is None:
            self.stop(T("Pédale déconnectée : auto-test arrêté."))
            return
        el = time.monotonic() - c["t0"]
        if not c["measuring"]:
            self.bar.setValue(int(min(1.0, el / self.SETTLE_S) * 100))
            if el >= self.SETTLE_S:             # réglage pris en compte : on mesure
                c["measuring"], c["t0"] = True, time.monotonic()
                info.ext_acc = new_ext_acc()
                self.pos = []
                if c["kind"] == "speed":
                    self.todo.setText(T("Appuie et relâche doucement, plusieurs fois… (mesure en cours)"))
            return
        dur = self.REST_S if c["kind"] == "rest" else self.MOVE_S
        self.bar.setValue(int(min(1.0, el / dur) * 100))
        if el < dur:
            return
        self.timer.stop()
        a = info.ext_acc
        if a["n"] < 20:
            self.stop(T("La pédale n'envoie pas son état détaillé : auto-test impossible avec ce firmware."))
            return
        mean = a["r"] / a["n"]
        sd = math.sqrt(max(0.0, a["rr"] / a["n"] - mean * mean))
        if c["kind"] == "rest":
            self.noise = sd
            self.results.append(("rest", None, sd, True))
            self._say(T("Bruit du capteur au repos : {n:.2f} kg (écart type).").format(n=sd))
            self._next()
            return
        travel = (max(self.pos) - min(self.pos)) if self.pos else 0.0
        if travel < MIN_TRAVEL:
            if c["tries"] < 2:
                self._say(T("Pédale trop peu bougée ({t:.0f} % de course) : on recommence ce palier.").format(t=travel))
                c["retry"], c["tries"] = True, c["tries"] + 1
                self.steps.insert(0, (c["kind"], c["kw"]))
                self._next()
                return
            self._say(T("Pédale toujours trop peu bougée : palier compté tel quel."))
        osc = a["osc"] / a["n"]
        ok = osc <= OSC_MAX
        kw = c["kw"]
        self.results.append(("speed", kw, osc, ok))
        self._say(T("Vitesse {s}, amortissement {d} % : {o:.1f} % du temps en oscillation → {r}").format(
            s=kw["kfModelNoise_u8"], d=kw["virtualPedalDampingInPercent_u8"], o=osc * 100,
            r=T("stable") if ok else T("vibre")))
        if not self.steps and not any(r[3] for r in self.results if r[0] == "speed") \
                and kw["virtualPedalDampingInPercent_u8"] < DAMPINGS[-1]:
            # tous les paliers vibrent : on garde la vitesse la plus calme et on monte l'amortissement
            for d in DAMPINGS:
                if d > kw["virtualPedalDampingInPercent_u8"]:
                    self.steps.append(("speed", {"kfModelOrder_u8": IMM, "kfModelNoise_u8": SPEEDS[-1],
                                                 "virtualPedalDampingInPercent_u8": d}))
            self._say(T("Tous les paliers vibrent : essai avec plus d'amortissement."))
        self._next()

    def _finish(self):
        self.timer.stop()
        good = [r for r in self.results if r[0] == "speed" and r[3]]
        if good:
            kw = good[0][1]
            self.final = self._cfg(**kw)
            self.final["debugFlags0_u8"] = self.orig["debugFlags0_u8"]
            self._send(self.final)
            self.step_lbl.setText(T("Résultat : vitesse du filtre {s}, amortissement {d} %").format(
                s=kw["kfModelNoise_u8"], d=kw["virtualPedalDampingInPercent_u8"]))
            self.todo.setText(T("Réglage appliqué (pas encore enregistré). Essaie la pédale, puis garde-le ou "
                                "reviens à tes réglages d'avant."))
        else:
            self.final = None
            self._send(self.orig)
            self.step_lbl.setText(T("Aucun réglage stable trouvé"))
            self.todo.setText(T("Même au plus calme, la pédale vibre : réglages d'avant remis. Vérifie la mécanique "
                                "(jeu, frottements), la précharge et le début de la courbe de force."))
        self.cur = None
        self.bar.setValue(100)
        self._buttons()

    def stop(self, msg):
        self.timer.stop()
        was = self.cur is not None or self.final is not None
        self.cur, self.steps, self.final = None, [], None
        if was and self.orig is not None and self.p.m.info(self.port):
            self.p.m.send_config(self.port, self.orig, False)
        self.step_lbl.setText("")
        self.todo.setText(msg)
        self._say(msg)
        self._buttons()

    def keep(self):
        if self.final is None:
            return
        if QMessageBox.question(self, T("Enregistrer dans la pédale"),
                                T("Enregistrer ce réglage de filtre dans la pédale ?")) != QMessageBox.Yes:
            return
        err = self.p.m.send_config(self.port, self.final, True)
        if err:
            QMessageBox.warning(self, T("Pédale"), T("Réglages refusés (la pédale les ignorerait) : {e}").format(e=err))
            return
        self.final = None
        self.todo.setText(T("Réglage enregistré dans la pédale."))
        self._buttons()

    def back(self):
        self.stop(T("Réglages d'avant remis (rien n'a été enregistré)."))

    def _say(self, line):
        self.log.appendPlainText(time.strftime("%H:%M:%S  ") + line)

    def refresh(self):
        """Appelé par la page (changement de pédale, configuration lue)."""
        if self.cur is None:
            self._buttons()
