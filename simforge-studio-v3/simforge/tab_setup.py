"""Onglet Mise en route : calibrations ODrive pas à pas, avec vérification des résultats."""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QCheckBox,
                               QScrollArea, QMessageBox)

from . import ow_protocol as P
from .i18n import T
from .theme import C
from .widgets import card, hint, Led, StatRow

GUARD_DPS = 360.0


class Step(QWidget):
    """Carte d'étape : numéro, titre, voyant, texte de résultat."""

    def __init__(self, n, title, text):
        super().__init__()
        self.c, self.l = card(f"{n}. {title}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.c)
        head = QHBoxLayout()
        self.led = Led(C["dim"], 10)
        head.addWidget(self.led, 0, Qt.AlignTop)
        self.txt = hint(text)
        head.addWidget(self.txt, 1)
        self.l.addLayout(head)
        self.res = QLabel("")
        self.res.setWordWrap(True)
        self.l.addWidget(self.res)
        self.btns = QHBoxLayout()
        self.l.addLayout(self.btns)
        self.btns.addStretch()

    def button(self, text, fn, primary=False):
        b = QPushButton(text)
        if primary:
            b.setObjectName("primary")
        b.clicked.connect(fn)
        self.btns.insertWidget(self.btns.count() - 1, b)
        return b

    def result(self, text, level="info"):
        col = {"ok": C["ok"], "warn": C["warn"], "bad": C["bad"], "run": C["blue"]}.get(level, C["dim"])
        self.res.setText(text)
        self.res.setStyleSheet(f"color: {col};")
        self.led.set(col)


class SetupTab(QWidget):
    goto_settings = Signal(int)

    def __init__(self, board, settings, parent=None):
        super().__init__(parent)
        self.b = board
        self.settings = settings        # pour lire les valeurs connues (rows[...].device)
        self.running = None             # (étape, état ODrive, t0)
        self.cpr_start = None
        self.last = None
        self.motor_ok = False
        self.guard_mine = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(10)
        # ------------------------------------------------ bandeau d'état
        top, tl = card(T("État de la carte"))
        g = QGridLayout()
        self.s_state = StatRow(T("État de l'axe"))
        self.s_vbus = StatRow(T("Tension bus"), "V")
        self.s_vel = StatRow(T("Vitesse"), "°/s")
        self.s_iq = StatRow(T("Courant moteur (Iq)"), "A")
        for i, w in enumerate((self.s_state, self.s_vbus, self.s_vel, self.s_iq)):
            w.v.setMinimumWidth(110)
            g.addWidget(w, 0, i)
        g.setColumnStretch(0, 3)
        tl.addLayout(g)
        self.err_lbl = QLabel("")
        self.err_lbl.setWordWrap(True)
        tl.addWidget(self.err_lbl)
        root.addWidget(top)

        inner = QWidget()
        cols = QHBoxLayout(inner)
        cols.setContentsMargins(0, 0, 6, 0)
        cols.setSpacing(12)
        left, right = QVBoxLayout(), QVBoxLayout()
        left.setSpacing(12)
        right.setSpacing(12)

        # ------------------------------------------------ 0. sécurité
        s0 = Step(0, T("Avant de commencer"),
                  T("Les calibrations font tourner le moteur. Coche chaque point : les boutons de lancement restent "
                    "grisés tant que tout n'est pas coché."))
        self.checks = []
        for t in (T("Jante enlevée : rien ne peut être frappé si le moteur tourne"),
                  T("Coupure de l'alimentation (interrupteur batterie) à portée de main"),
                  T("Codeur branché sur le connecteur M0, broche Z vide"),
                  T("Résistance de freinage branchée et vissée sur une plaque métallique")):
            cb = QCheckBox(t)
            cb.toggled.connect(self._safety)
            s0.l.insertWidget(s0.l.count() - 1, cb)
            self.checks.append(cb)
        left.addWidget(s0)

        # ------------------------------------------------ 1. alimentation
        self.s1 = Step(1, T("Alimentation et protections"),
                       T("La tension mesurée doit être entre les seuils de coupure, et la résistance de freinage "
                         "déclarée. Ces réglages se trouvent dans Réglages › Alimentation."))
        self.s1.button(T("Ouvrir Réglages › Alimentation"), lambda: self.goto_settings.emit(3))
        left.addWidget(self.s1)

        # ------------------------------------------------ 2. erreurs
        self.s2 = Step(2, T("Effacer les erreurs"),
                       T("Une erreur présente bloque toute calibration. L'effacement réarme aussi la résistance de "
                         "freinage."))
        self.s2.button(T("Effacer les erreurs"), self.b.clear_errors)
        left.addWidget(self.s2)

        # ------------------------------------------------ 3. moteur
        self.s3 = Step(3, T("Calibration moteur"),
                       T("Le moteur siffle quelques secondes sans tourner : la carte mesure la résistance et "
                         "l'inductance des phases. Paires de pôles et courant de calibration doivent être réglés "
                         "avant (Réglages › Moteur et codeur)."))
        self.b3 = self.s3.button(T("Lancer la calibration moteur"), lambda: self.run(3, 4), True)
        self.b3b = self.s3.button(T("Valider : moteur calibré"), self.mark_motor)
        self.b3b.setEnabled(False)
        left.addWidget(self.s3)
        left.addStretch()

        # ------------------------------------------------ 4. codeur
        self.s4 = Step(4, T("Calage du codeur"),
                       T("Le moteur tourne lentement d'environ un tour dans un sens puis dans l'autre. Le sens du "
                         "codeur est trouvé automatiquement : pas besoin d'inverser A et B."))
        self.b4 = self.s4.button(T("Lancer le calage"), lambda: self.run(4, 7), True)
        right.addWidget(self.s4)

        # ------------------------------------------------ 5. CPR
        self.s5 = Step(5, T("Vérifier le CPR (un tour à la main)"),
                       T("Moteur au repos : clique « Départ », fais exactement un tour de moteur à la main "
                         "(repère au feutre), puis « Arrivée ». Le compteur doit avancer du CPR réglé."))
        self.b5a = self.s5.button(T("Départ"), self.cpr_begin)
        self.b5b = self.s5.button(T("Arrivée"), self.cpr_end)
        self.b5b.setEnabled(False)
        right.addWidget(self.s5)

        # ------------------------------------------------ 6. boucle fermée
        self.s6 = Step(6, T("Essai en boucle fermée"),
                       T("Le moteur est actif mais aucun jeu n'envoie de force : à la main, il doit tourner librement "
                         "(ou freiner légèrement), sans à-coups, sans partir tout seul. Coupure automatique au-delà "
                         "de {v} °/s.").format(v=f"{GUARD_DPS:.0f}"))
        self.b6 = self.s6.button(T("Activer le moteur"), lambda: self.run(6, 8), True)
        self.s6.button(T("Repos"), lambda: self.b.request_state(1))
        right.addWidget(self.s6)

        # ------------------------------------------------ 7. démarrage
        self.s7 = Step(7, T("Volant prêt dès l'allumage"),
                       T("Sans ce réglage, la carte démarre moteur coupé et il faut refaire l'étape 4 à chaque fois.\n"
                         "Ce bouton règle la carte pour qu'à chaque allumage elle cale le codeur toute seule (le "
                         "volant bouge d'environ un tour), puis active le moteur.\n"
                         "À faire une seule fois, après les étapes 3 et 4."))
        self.s7.button(T("Régler le démarrage automatique"), self.apply_startup, True)
        right.addWidget(self.s7)
        right.addStretch()

        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setWidget(inner)
        root.addWidget(sc, 1)

        self.b.telemetry.connect(self.on_telemetry)
        self.b.values.connect(self.on_values)
        self.b.link_changed.connect(lambda _i: self._safety())
        self._safety()
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(200)

    # ------------------------------------------------------------ outils
    def dev(self, path):
        r = self.settings.rows.get(path)
        return r.device if r else None

    def _safe(self):
        return all(cb.isChecked() for cb in self.checks)

    def _safety(self):
        ok = self._safe() and self.b.serial_ok
        for b in (self.b3, self.b4, self.b6):
            b.setEnabled(ok and self.running is None)
            b.setToolTip("" if ok else T("Coche d'abord toutes les précautions de l'étape 0 (et connecte la carte)."))

    # ------------------------------------------------------------ étapes
    def run(self, step, st):
        if self.b.estop:
            QMessageBox.information(self, T("STOP enclenché"), T("Réarme le STOP en haut à droite avant de lancer."))
            return
        if self.last and self.last.any_error:
            QMessageBox.information(self, T("Erreurs présentes"),
                                    T("Efface d'abord les erreurs (étape 2) : la carte refuserait la commande."))
            return
        if st == 7 and not self.dev("axis0.motor.config.pre_calibrated") and not self.motor_ok:
            if QMessageBox.question(self, T("Calage du codeur"),
                                    T("Le moteur n'est pas marqué comme calibré. Le calage échouera si la "
                                      "calibration moteur n'a pas été faite depuis l'allumage. Continuer ?")) \
                    != QMessageBox.Yes:
                return
        if st == 8 and QMessageBox.question(
                self, T("Activer le moteur"),
                T("Le moteur va être alimenté. Garde la main sur la coupure d'alimentation. Continuer ?")) \
                != QMessageBox.Yes:
            return
        if not self.b.request_state(st):
            return
        # calibrations : survitesse retenue seulement si elle dure 150 ms (le saut de calage dure quelques ms)
        self.b.arm_guard(True, GUARD_DPS, range_check=(st == 8), sustain_s=0.15 if st in (4, 7) else 0.0)
        self.guard_mine = True
        self.running = (step, st, time.perf_counter(), False)
        {3: self.s3, 4: self.s4, 6: self.s6}[step].result(T("En cours…"), "run")
        self._safety()

    def _finish(self):
        step, st, t0, seen = self.running
        self.running = None
        self.b.arm_guard(False)
        self.guard_mine = False
        self._safety()
        box = {3: self.s3, 4: self.s4}[step]
        if not seen:
            errs = P.errors_of(self.last) if self.last else []
            box.result(T("✖ La carte n'a pas lancé l'opération : ") +
                       ("; ".join(f"{n} — {d}" for _g, n, d in errs) or
                        (T("STOP enclenché.") if self.b.estop else T("aucune erreur remontée, réessaie."))), "bad")
            return
        if step == 3:
            self.b.read(["axis0.motor.config.phase_resistance", "axis0.motor.config.phase_inductance",
                         "axis0.motor.error", "axis0.error"], "setup3")
        elif step == 4:
            self.b.read(["axis0.encoder.is_ready", "axis0.encoder.error", "axis0.encoder.config.direction",
                         "axis0.error"], "setup4")

    def _tick(self):
        if not self.running or not self.last:
            return
        step, st, t0, seen = self.running
        cur = self.last.state
        el = time.perf_counter() - t0
        if not seen and cur == st:
            self.running = (step, st, t0, True)
            return
        if step == 6:
            if cur == P.CLOSED_LOOP:
                self.s6.result(T("✔ Boucle fermée active. Tourne le moteur à la main pour vérifier."), "ok")
                self.running = None
                self._safety()
            elif (seen or el > 1.5) and cur != P.CLOSED_LOOP:
                self.running = None
                self.b.arm_guard(False)
                self.guard_mine = False
                self._safety()
                errs = P.errors_of(self.last)
                self.s6.result(T("✖ Refusé : ") + ("; ".join(f"{n} — {d}" for _g, n, d in errs) or
                                                     T("l'axe est resté au repos.")), "bad")
            return
        if (seen and cur != st) or (not seen and el > 2.0):
            self._finish()
        elif el > 60:
            self._finish()

    def mark_motor(self):
        self.b.write("axis0.motor.config.pre_calibrated", 1)
        self.s3.result(self.s3.res.text() + "\n" + T("Moteur marqué comme calibré (à mémoriser avec « Enregistrer »)."),
                       "ok")
        self.b3b.setEnabled(False)

    def cpr_begin(self):
        if self.last and self.last.state != P.IDLE:
            QMessageBox.information(self, T("CPR"), T("Mets d'abord le moteur au repos (bouton Repos, étape 6)."))
            return
        self.b.read(["axis0.encoder.shadow_count"], "cpr0")

    def cpr_end(self):
        self.b.read(["axis0.encoder.shadow_count", "axis0.encoder.config.cpr"], "cpr1")

    def apply_startup(self):
        want = {"axis0.motor.config.pre_calibrated": 1, "axis0.config.startup_motor_calibration": 0,
                "axis0.config.startup_encoder_index_search": 0, "axis0.encoder.config.use_index": 0,
                "axis0.encoder.config.pre_calibrated": 0, "axis0.config.startup_encoder_offset_calibration": 1,
                "axis0.config.startup_closed_loop_control": 1, "axis0.controller.config.control_mode": 1,
                "axis0.controller.config.input_mode": 1}
        if self.dev("axis0.motor.config.phase_resistance") in (None, 0, 0.0):
            QMessageBox.warning(self, T("Démarrage automatique"),
                                T("Fais d'abord la calibration moteur (étape 3) : « moteur déjà calibré » "
                                  "n'a de sens qu'après."))
            return
        for p, v in want.items():
            self.settings.on_edit(p, v)
            self.settings.rows[p]._style("pending")
        self.settings._flush()
        self.s7.result(T("C'est réglé, mais pas encore mémorisé. Clique « Enregistrer dans la carte » en bas à "
                         "droite : la carte redémarre et fait son tour de calage (lâche le volant)."), "ok")

    # ------------------------------------------------------------ données
    def on_values(self, vals, tag):
        num = lambda k: P.Field("", "", "float").parse(vals.get(k)) if vals.get(k) is not None else None
        if tag == "setup3":
            r, l = num("axis0.motor.config.phase_resistance"), num("axis0.motor.config.phase_inductance")
            me = int(num("axis0.motor.error") or 0)
            errs = P.decode("motor", me)
            if errs:
                self.s3.result(T("✖ Échec : ") + "; ".join(f"{n} — {d}" for n, d in errs), "bad")
                return
            if r is None or l is None or r <= 0:
                self.s3.result(T("✖ Pas de mesure : la calibration n'a pas abouti (STOP ? erreur ?)."), "bad")
                return
            ok = 0.02 <= r <= 2.0 and 5e-6 <= l <= 3e-3
            self.s3.result((T("✔") if ok else T("⚠")) + " " +
                           T("Résistance {r} Ω, inductance {l} µH.").format(r=f"{r:.4f}", l=f"{l * 1e6:.0f}") + " " +
                           (T("Valeurs cohérentes pour un moteur de volant.") if ok else
                            T("Valeurs inhabituelles : vérifie les fils moteur et les réglages de calibration.")),
                           "ok" if ok else "warn")
            self.b3b.setEnabled(ok)
            self.motor_ok = ok
        elif tag == "setup4":
            ready = vals.get("axis0.encoder.is_ready") == "1"
            ee = int(num("axis0.encoder.error") or 0)
            errs = P.decode("encoder", ee)
            d = vals.get("axis0.encoder.config.direction")
            if errs or not ready:
                hint_ = ""
                if ee & 0x2:
                    hint_ = "\n" + T("CPR ou paires de pôles faux : vérifie le CPR (PPR × 4 × rapport) et le nombre de paires de pôles.")
                elif ee & 0x4:
                    hint_ = "\n" + T("Le codeur ne compte pas : alimentation 5 V, GND, A/B et résistances de tirage.")
                self.s4.result(T("✖ Échec : ") + ("; ".join(f"{n} — {x}" for n, x in errs) or T("codeur pas prêt"))
                               + hint_, "bad")
            else:
                self.s4.result(T("✔ Codeur calé, sens trouvé : {d}. Le moteur peut passer en boucle fermée.")
                               .format(d=d), "ok")
        elif tag == "cpr0":
            v = num("axis0.encoder.shadow_count")
            if v is None:
                self.s5.result(T("Lecture impossible."), "bad")
                return
            self.cpr_start = v
            self.b5b.setEnabled(True)
            self.s5.result(T("Départ noté ({v}). Fais un tour complet puis « Arrivée ».").format(v=int(v)), "run")
        elif tag == "cpr1" and self.cpr_start is not None:
            v, cpr = num("axis0.encoder.shadow_count"), num("axis0.encoder.config.cpr")
            self.b5b.setEnabled(False)
            if v is None or not cpr:
                self.s5.result(T("Lecture impossible."), "bad")
                return
            d = abs(v - self.cpr_start)
            err = (d - cpr) / cpr * 100
            ok = abs(err) <= 3
            self.s5.result((T("✔") if ok else T("⚠")) + " " +
                           T("{d} points comptés pour {c} réglés ({e} %).").format(d=int(d), c=int(cpr), e=f"{err:+.1f}")
                           + ("" if ok else " " + T("Refais un tour bien exact ; si l'écart persiste, le CPR est faux.")),
                           "ok" if ok else "warn")
            self.cpr_start = None

    def on_telemetry(self, batch):
        tm = batch[-1]
        self.last = tm
        if self.guard_mine and self.running is None and tm.state != P.CLOSED_LOOP:
            self.b.arm_guard(False)
            self.guard_mine = False
        if not self.isVisible():
            return
        self.s_state.set(P.state_text(tm.state), C["ok"] if tm.state == P.CLOSED_LOOP else
                         C["blue"] if tm.state in P.CALIBRATING else None)
        self.s_vbus.set(f"{tm.vbus:.2f}")
        self.s_vel.set(f"{tm.speed_dps:+.0f}")
        self.s_iq.set(f"{tm.iq:+.2f}")
        errs = P.errors_of(tm)
        self.err_lbl.setText("\n".join(f"✖ {g} · {n} — {d}" for g, n, d in errs) if errs else T("Aucune erreur."))
        self.err_lbl.setStyleSheet(f"color: {C['bad'] if errs else C['ok']};")
        if errs:
            self.s2.result(T("{n} erreur(s) présente(s).").format(n=len(errs)), "bad")
        else:
            self.s2.result(T("Aucune erreur."), "ok")
        # alimentation
        lo, hi = self.dev("config.dc_bus_undervoltage_trip_level"), self.dev("config.dc_bus_overvoltage_trip_level")
        br, en = self.dev("config.brake_resistance"), self.dev("config.enable_brake_resistor")
        if lo is None or hi is None:
            self.s1.result(T("Réglages pas encore lus."))
        else:
            probs = []
            if not lo < tm.vbus < hi:
                probs.append(T("tension {v} V hors de {a}–{b} V").format(v=f"{tm.vbus:.1f}", a=f"{lo:.0f}", b=f"{hi:.0f}"))
            if not en:
                probs.append(T("résistance de freinage désactivée"))
            elif not br or br < 0.2:
                probs.append(T("valeur de résistance de freinage suspecte ({r} Ω)").format(r=br))
            if hi - tm.vbus < 2.5 and lo < tm.vbus < hi:
                probs.append(T("seuil haut très proche de la tension actuelle"))
            if probs:
                self.s1.result("⚠ " + " · ".join(probs), "warn")
            else:
                self.s1.result(T("✔ {v} V entre {a} et {b} V · résistance {r} Ω active.").format(
                    v=f"{tm.vbus:.1f}", a=f"{lo:.0f}", b=f"{hi:.0f}", r=f"{br:g}"), "ok")
