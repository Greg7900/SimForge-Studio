"""Fenêtre principale SimForge Studio V3 : volant Odrive-Wheel + pédales actives ChrGri, menu à gauche."""
from __future__ import annotations

import os
import sys
import time

from PySide6.QtCore import Qt, QProcess, QEvent
from PySide6.QtGui import QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QStackedWidget, QListWidget, QListWidgetItem, QPlainTextEdit, QMessageBox,
                               QComboBox, QScrollArea, QFrame, QApplication)

from . import i18n
from . import ow_protocol as P
from .i18n import T
from .ow_device import Board
from .ped_device import PedalManager
from .tab_overview import OverviewTab
from .tab_pedals import PedalsTab
from .tab_pedal_fw import PedalFirmwareTab
from .sdl_input import SdlInput
from .tab_console import ConsoleTab
from .tab_encoder import EncoderTab
from .tab_force import ForceTab
from .tab_joy import JoyTab
from .tab_monitor import MonitorTab
from .tab_overlay import OverlayTab
from .tab_params import SettingsTab
from .tab_setup import SetupTab
from .theme import C
from .widgets import Led, hint, install_wheel_guard

VERSION = "3.0"
TARGET_BASE = ("0", "5", "6")


class _Fit(QWidget):
    """Conteneur de page sans layout : la page prend exactement la taille visible. QScrollArea ne défile donc que
    si la fenêtre est plus petite que le minimum de la page (un layout avec du texte à la ligne lui faisait
    calculer une hauteur « selon la largeur » trop grande, et la page dépassait en bas)."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        page.setParent(self)

    def minimumSizeHint(self):
        return self.page.minimumSizeHint()

    def sizeHint(self):
        return self.page.minimumSizeHint()

    def resizeEvent(self, e):
        self.page.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(e)

    def event(self, e):
        if e.type() == QEvent.LayoutRequest:      # la page a changé de taille mini (ex. réglages avancés)
            self.updateGeometry()
        return super().event(e)


class MainWindow(QMainWindow):
    def __init__(self, demo=False, icon_path=None):
        super().__init__()
        self.setWindowTitle(f"SimForge Studio V{VERSION}" + (T("  —  DÉMO (matériel simulé)") if demo else ""))
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1400, 900)
        install_wheel_guard(QApplication.instance())
        self.b = Board(demo=demo)
        self.pm = PedalManager(demo=demo)
        self.sdl = SdlInput()
        self.warned_fw = False
        self.dirty = (False, False)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ---------------------------------------------- en-tête
        head = QWidget()
        head.setObjectName("head")
        head.setAttribute(Qt.WA_StyledBackground, True)
        head.setStyleSheet(f"QWidget#head {{ background: {C['panel']}; border-bottom: 1px solid {C['line']}; }}")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(14, 10, 12, 10)
        hl.setSpacing(4)
        brand = QLabel(f'SIMFORGE<span style="color:{C["accent"]}; font-weight:300;"> STUDIO</span>')
        brand.setObjectName("brand")
        brand.setTextFormat(Qt.RichText)
        hl.addWidget(brand)
        ver = QLabel(f"V{VERSION}")
        ver.setObjectName("hint")
        hl.addWidget(ver, 0, Qt.AlignBottom)
        if demo:
            d = QLabel(T("DÉMO"))
            d.setObjectName("badge")
            hl.addWidget(d, 0, Qt.AlignVCenter)
        hl.addSpacing(16)
        self.led_s = Led(C["bad"], 10)
        self.led_s.setToolTip(T("Port série : réglages et commandes"))
        hl.addWidget(self.led_s)
        ls = QLabel(T("Réglages"))
        ls.setObjectName("hint")
        ls.setToolTip(self.led_s.toolTip())
        hl.addWidget(ls)
        hl.addSpacing(8)
        self.led_h = Led(C["bad"], 10)
        self.led_h.setToolTip(T("HID : télémétrie à 1 kHz et retour de force"))
        hl.addWidget(self.led_h)
        lh = QLabel(T("Mesures"))
        lh.setObjectName("hint")
        lh.setToolTip(self.led_h.toolTip())
        hl.addWidget(lh)
        hl.addSpacing(8)
        self.led_p = Led(C["bad"], 10)
        hl.addWidget(self.led_p)
        self.lp = QLabel(T("Pédales {n}").format(n=0))
        self.lp.setObjectName("hint")
        self.lp.setFixedWidth(self.lp.fontMetrics().horizontalAdvance(T("Pédales {n}").format(n=8)) + 6)
        hl.addWidget(self.lp)
        self.led_p.setToolTip(T("Pédales actives détectées (port série de chaque pédale)"))
        self.lp.setToolTip(self.led_p.toolTip())
        hl.addSpacing(12)
        self.conn = QLabel(T("Recherche de la carte…"))
        self.conn.setFixedWidth(150)       # largeur fixe : le texte change sans décaler l'en-tête
        hl.addWidget(self.conn)
        self._port = ""
        hl.addSpacing(14)
        self.state = QLabel("")
        self.state.setStyleSheet(f"font-weight: 700; color: {C['dim']};")
        self.state.setFixedWidth(175)      # largeur fixe : l'en-tête ne bouge pas quand l'état change
        hl.addWidget(self.state)
        self.live = QLabel("")
        self.live.setStyleSheet(f"font-family: Consolas, monospace; font-size: 11pt; color: {C['dim']};")
        self.live.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        from PySide6.QtGui import QFont, QFontMetrics
        _f = QFont("Consolas")
        _f.setPointSize(11)
        self.live.setMaximumWidth(QFontMetrics(_f).horizontalAdvance("+0000.0°   +00.00 N·m   00.0 V") + 24)
        from PySide6.QtWidgets import QSizePolicy
        self.live.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # se réduit au lieu d'élargir la fenêtre
        self.live.hide()              # valeurs en direct : onglet Moniteur (un texte tronqué ici serait trompeur)
        hl.addStretch(1)
        hl.addSpacing(12)
        self.lang = QComboBox()
        for code, name in i18n.LANGS.items():
            self.lang.addItem(name, code)
        self.lang.setCurrentIndex(list(i18n.LANGS).index(i18n.LANG))
        self.lang.setToolTip("Language / Langue")
        self.lang.currentIndexChanged.connect(self.change_lang)
        hl.addWidget(self.lang)
        hl.addSpacing(8)
        self.b_arm = QPushButton(T("Activer le moteur"))
        self.b_arm.setToolTip(T("Passe l'axe en boucle fermée : le moteur est alimenté et applique les forces."))
        self.b_arm.clicked.connect(self.arm_motor)
        hl.addWidget(self.b_arm)
        hl.addSpacing(6)
        self.estop = QPushButton(T("STOP VOLANT"))
        self.estop.setObjectName("estop")
        self.estop.setToolTip(T("Met l'axe au repos : le moteur n'est plus alimenté du tout (jeux compris) et le reste "
                                "tant que le STOP est enclenché. Raccourci : Échap.\nNe remplace pas la coupure "
                                "matérielle de l'alimentation."))
        self.estop.setCursor(Qt.PointingHandCursor)
        self.estop.clicked.connect(self.toggle_estop)
        hl.addWidget(self.estop)
        lay.addWidget(head)

        # ---------------------------------------------- menu à gauche + pages
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(196)
        self.nav.setFocusPolicy(Qt.NoFocus)
        self.nav.setStyleSheet(
            f"QListWidget#nav {{ background: {C['panel']}; border: none; border-right: 1px solid {C['line']};"
            f" padding-top: 6px; outline: 0; }}"
            f"QListWidget#nav::item {{ padding: 7px 14px; color: {C['text']}; border: none; }}"
            f"QListWidget#nav::item:selected {{ background: {C['bg']}; color: {C['accent']};"
            f" border-left: 3px solid {C['accent']}; }}"
            f"QListWidget#nav::item:hover:!selected {{ background: {C['bg']}; }}")
        self.pages = QStackedWidget()
        bl.addWidget(self.nav)
        bl.addWidget(self.pages, 1)

        self.settings = SettingsTab(self.b)
        self.setup = SetupTab(self.b, self.settings)
        self.monitor = MonitorTab(self.b, self.settings)
        self.encoder = EncoderTab(self.b, self.settings)
        self.overlay = OverlayTab(self.b, self.settings)
        self.joy = JoyTab(self.sdl)
        self.force = ForceTab(self.b, self.sdl, self.settings)
        self.console = ConsoleTab(self.b)
        self.overview = OverviewTab(self.b, self.pm)
        self.ped = PedalsTab(self.pm)
        self.ped_fw = PedalFirmwareTab(self.pm)
        self.journal = QPlainTextEdit()
        self.journal.setObjectName("console")
        self.journal.setReadOnly(True)
        self.journal.setMaximumBlockCount(4000)
        jw = QWidget()
        jl = QVBoxLayout(jw)
        jl.setContentsMargins(16, 12, 16, 12)
        jl.addWidget(hint(T("Toutes les commandes envoyées et les événements de connexion (volant et pédales).")))
        jl.addWidget(self.journal)
        self.page_key = {}
        self.wheel_pages = set()
        menu = [
            (None, "overview", T("Vue d'ensemble"), self.overview),
            (T("VOLANT"), None, None, None),
            ("w", "w_setup", T("Mise en route"), self.setup),
            ("w", "w_settings", T("Réglages"), self.settings),
            ("w", "w_monitor", T("Moniteur"), self.monitor),
            ("w", "w_encoder", T("Codeur"), self.encoder),
            ("w", "w_force", "Force test", self.force),
            (T("PÉDALES"), None, None, None),
            ("p", "p_settings", T("Réglages"), self.ped),
            ("p", "p_fw", T("Firmware"), self.ped_fw),
            (T("OUTILS"), None, None, None),
            ("t", "t_joy", "Joy tester", self.joy),
            ("t", "t_overlay", "Overlay", self.overlay),
            ("t", "t_console", T("Console volant"), self.console),
            ("t", "t_log", T("Journal"), jw),
        ]
        for grp, key, label, w in menu:
            if key is None:
                it = QListWidgetItem(grp)
                it.setFlags(Qt.NoItemFlags)
                f = it.font()
                f.setPointSizeF(f.pointSizeF() * 0.85)
                f.setBold(True)
                it.setFont(f)
                it.setForeground(Qt.gray)
                self.nav.addItem(it)
                continue
            it = QListWidgetItem(("    " if grp else "") + label)
            it.setData(Qt.UserRole, key)
            self.nav.addItem(it)
            # chaque page dans une zone défilante : une page large ne force plus la largeur minimale de la fenêtre
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.NoFrame)
            sa.setWidget(_Fit(w))
            self.pages.addWidget(sa)
            self.page_key[key] = (it, sa)
            if grp == "w":
                self.wheel_pages.add(key)
        self.nav.currentItemChanged.connect(self._nav)
        lay.addWidget(body, 1)
        self.setup.goto_settings.connect(self.goto_settings)
        self.overview.goto.connect(self.goto)

        # ---------------------------------------------- barre d'actions globale
        act = QWidget()
        act.setObjectName("actbar")
        act.setAttribute(Qt.WA_StyledBackground, True)
        act.setStyleSheet(f"QWidget#actbar {{ background: {C['panel']}; border-top: 1px solid {C['line']}; }}")
        al = QHBoxLayout(act)
        al.setContentsMargins(16, 8, 16, 8)
        al.setSpacing(8)
        self.b_center = QPushButton(T("Recentrer le volant"))
        self.b_center.setToolTip(T("Le volant prend sa position actuelle comme centre (mémorisé avec « Enregistrer »)."))
        self.b_center.clicked.connect(self.b.recenter)
        self.b_clear = QPushButton(T("Effacer les erreurs"))
        self.b_clear.clicked.connect(self.b.clear_errors)
        self.dirty_lbl = QLabel("")
        self.dirty_lbl.setObjectName("hint")
        self.b_dfu = QPushButton(T("Mode DFU…"))
        self.b_dfu.setObjectName("danger")
        self.b_dfu.setToolTip(T("Redémarre la carte dans son chargeur DFU pour la reflasher (STM32CubeProgrammer), "
                                "sans toucher à l'interrupteur."))
        self.b_dfu.clicked.connect(self.dfu)
        self.b_reboot = QPushButton(T("Redémarrer la carte"))
        self.b_reboot.clicked.connect(self.reboot)
        self.b_save = QPushButton(T("Enregistrer dans la carte"))
        self.b_save.setObjectName("primary")
        self.b_save.setToolTip(T("Mémorise les réglages volant/effets (sans redémarrer) et, s'il y en a, les réglages "
                                 "ODrive (moteur au repos, la carte redémarre et refait son calage)."))
        self.b_save.clicked.connect(self.save)
        al.addWidget(self.b_center)
        al.addWidget(self.b_clear)
        al.addStretch()
        al.addWidget(self.dirty_lbl)
        al.addSpacing(10)
        al.addWidget(self.b_dfu)
        al.addWidget(self.b_reboot)
        al.addWidget(self.b_save)
        lay.addWidget(act)
        self.actbar = act
        self.statusBar().showMessage(T("Prêt"))

        # ---------------------------------------------- liaisons
        b = self.b
        b.link_changed.connect(self.on_link)
        b.log.connect(self.on_log)
        b.telemetry.connect(self.on_tm)
        b.guard_tripped.connect(self.on_guard)
        b.estop_changed.connect(self.on_estop_changed)
        b.saved.connect(self.on_saved)
        b.values.connect(self.on_values)
        b.rearm_needs_cal.connect(self.on_needs_cal)
        self.settings.dirty_changed.connect(self.on_dirty)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.engage_estop)
        self._set_actions()
        self.pm.log.connect(self.on_log)
        self.pm.changed.connect(self.on_pedals)
        b.start()
        self.pm.start()
        self.goto("w_settings")

    # ------------------------------------------------------------ journal / état
    def on_log(self, level, msg):
        if level == "debug":
            return
        color = {"warn": C["warn"], "error": C["bad"]}.get(level, C["dim"])
        esc = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.journal.appendHtml(f'<span style="color:{C["dim"]}">{time.strftime("%H:%M:%S")}</span> '
                                f'<span style="color:{color}">{esc}</span>')
        if level in ("warn", "error"):
            self.statusBar().showMessage(msg, 8000)

    def on_link(self, info):
        b = self.b
        self.led_s.set(C["ok"] if b.serial_ok else C["bad"])
        self.led_h.set(C["ok"] if b.hid_ok else C["bad"])
        if info.get("port"):
            self._port = str(info["port"])
        if b.serial_ok and b.hid_ok:
            self._set_conn(T("Connecté") + (f"  ·  {self._port}" if self._port else ""))
        elif b.serial_ok:
            self._set_conn(T("Port série seul (pas de télémétrie HID)"))
        elif b.hid_ok:
            self._set_conn(T("Télémétrie seule : port série occupé ? (ferme l'outil web)"))
            self.conn.setToolTip(self.conn.toolTip() + "\n" + T("Le port série ne peut être ouvert que par un seul programme à la fois : ferme "
                                   "l'outil web Odrive-Wheel, la console odrivetool ou SimHub (plugin Odrive-Wheel)."))
        else:
            why = info.get("why")
            self._set_conn(T("Déconnecté") + (f" — {why}" if why else ""))
            self.live.setText("")
            self.state.setText("")
        if info.get("serial") is False:
            self.force.stop_all() if not b.hid_ok else None
        if info.get("hwtype") and info["hwtype"] != "ODrive-Wheel":
            QMessageBox.warning(self, T("Firmware"), T("La carte répond « {h} » : SimForge Studio V3 est fait pour le "
                                                       "firmware Odrive-Wheel.").format(h=info["hwtype"]))
        self._set_actions()

    def _set_conn(self, text):
        """Texte de connexion raccourci à la largeur fixe ; le texte complet reste en infobulle."""
        self.conn.setText(self.conn.fontMetrics().elidedText(text, Qt.ElideRight, self.conn.width() - 2))
        self.conn.setToolTip(text)

    def on_values(self, vals, tag):
        if tag != "all" or self.warned_fw:
            return
        fw = tuple(vals.get(k) for k in ("fw_version_major", "fw_version_minor", "fw_version_revision"))
        hw = tuple(vals.get(k) for k in ("hw_version_major", "hw_version_minor", "hw_version_variant"))
        if None in fw:
            return
        self.warned_fw = True
        # Odrive-Wheel livre un autogen/version.c figé à 0.0.0 (« unreleased ») : c'est normal pour ce firmware,
        # la base 0.5.6 est garantie par son code source. On ne prévient que pour une autre version réelle.
        if fw not in (TARGET_BASE, ("0", "0", "0")):
            QMessageBox.warning(self, T("Version de firmware"),
                                T("La carte annonce une base ODrive {v}. SimForge Studio V3 a été écrit pour "
                                  "Odrive-Wheel sur ODrive 0.5.6 : vérifie les valeurs avant de les modifier.")
                                .format(v=".".join(fw)))
        if None not in hw and hw[:2] != ("3", "6"):
            self.on_log("warn", T("Matériel annoncé : v{h}").format(h=".".join(hw)))

    def on_tm(self, batch):
        tm = batch[-1]
        self.live.setText(f"{tm.pos:+7.1f}°   {tm.torque:+5.2f} N·m   {tm.vbus:4.1f} V")
        if tm.any_error:
            names = ", ".join(n for _g, n, _d in P.errors_of(tm))
            txt, col = T("ERREUR : {e}").format(e=names), C["bad"]
        elif tm.state == P.CLOSED_LOOP:
            txt, col = T("MOTEUR ACTIF"), C["ok"]
        elif tm.state in P.CALIBRATING:
            txt, col = P.STATES[tm.state][1].upper(), C["blue"]
        else:
            txt, col = T("MOTEUR AU REPOS"), C["warn"]
        if getattr(self, "_state_txt", None) != txt:
            self._state_txt = txt
            self.state.setText(self.state.fontMetrics().elidedText(txt, Qt.ElideRight, self.state.width() - 4))
            self.state.setStyleSheet(f"font-weight: 700; color: {col};")
            self.state.setToolTip("\n".join(f"{g} · {n} — {d}" for g, n, d in P.errors_of(tm)))
            self._set_actions()

    def _set_actions(self):
        b = self.b
        s = b.serial_ok
        for w in (self.b_center, self.b_clear, self.b_reboot, self.b_dfu, self.b_save):
            w.setEnabled(s)
        st = b.state
        # toujours présent (grisé si sans objet) : afficher/masquer le bouton décalait tout l'en-tête
        self.b_arm.setEnabled(s and not b.estop and st != P.CLOSED_LOOP and st not in P.CALIBRATING)

    def on_dirty(self, ffb, odrive):
        self.dirty = (ffb, odrive)
        parts = []
        if ffb:
            parts.append(T("réglages volant/effets"))
        if odrive:
            parts.append(T("réglages ODrive"))
        self.dirty_lbl.setText(T("Non mémorisé : {l}").format(l=" + ".join(parts)) if parts else "")
        self.dirty_lbl.setStyleSheet(f"color: {C['warn']};" if parts else "")

    def goto(self, key):
        it, _w = self.page_key[key]
        self.nav.setCurrentItem(it)

    def _nav(self, it, _prev):
        key = it.data(Qt.UserRole) if it else None
        if key not in self.page_key:
            return
        self.pages.setCurrentWidget(self.page_key[key][1])
        # la barre du bas (recentrer, enregistrer dans la carte…) ne concerne que le volant
        wheel = key in self.wheel_pages or key == "t_console"
        self.actbar.setVisible(wheel)
        # « Activer le moteur » et STOP ne pilotent que le volant : cachés ailleurs (Échap reste actif partout)
        self.b_arm.setVisible(wheel)
        self.estop.setVisible(wheel)

    def on_pedals(self):
        ps = self.pm.pedals()
        bad = any(p.incompatible for p in ps)
        self.led_p.set(C["bad"] if (bad or not ps) else C["ok"])
        self.lp.setText(T("Pédales {n}").format(n=len(ps)))
        self.lp.setToolTip("\n".join(p.name for p in ps) or T("Aucune pédale détectée"))

    def goto_settings(self, page):
        self.goto("w_settings")
        self.settings.tabs.setCurrentIndex(page)

    # ------------------------------------------------------------ actions
    def arm_motor(self):
        if QMessageBox.question(self, T("Activer le moteur"),
                                T("Le moteur va être alimenté et appliquer les forces (jeu, ressort au repos, butées). "
                                  "Garde la main près de la coupure d'alimentation. Continuer ?")) != QMessageBox.Yes:
            return
        self.b.request_state(P.CLOSED_LOOP)

    def on_needs_cal(self):
        r = QMessageBox.question(self, T("Codeur pas calé"),
                                 T("Le codeur n'a pas été calé depuis l'allumage : la carte ne sait pas où est le "
                                   "rotor. Lancer le calage maintenant ? Le moteur va tourner d'environ un tour : "
                                   "lâche le volant."))
        if r == QMessageBox.Yes:
            self.b.request_state(7)

    def save(self):
        st = self.settings
        if st.pending:
            r = QMessageBox.question(self, T("Enregistrer"),
                                     T("{n} modification(s) pas encore appliquée(s). Les appliquer avant "
                                       "d'enregistrer ?").format(n=len(st.pending)),
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Yes:
                st._flush()
                self.on_log("info", T("Modifications appliquées : clique de nouveau « Enregistrer » une fois relues."))
                return
        odrive = self.dirty[1]
        if not odrive:
            r = QMessageBox.question(self, T("Enregistrer"),
                                     T("Mémoriser les réglages volant et effets ?\n\nAucun réglage ODrive n'a été "
                                       "changé depuis la lecture. Mémoriser aussi la configuration ODrive (la carte "
                                       "redémarre) ?"),
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
            if r == QMessageBox.Cancel:
                return
            odrive = r == QMessageBox.Yes
        elif QMessageBox.question(self, T("Enregistrer"),
                                  T("Des réglages ODrive ont changé : le moteur va être mis au repos, la configuration "
                                    "mémorisée, puis la carte redémarre et refait son calage (le volant bouge "
                                    "d'environ un tour). Lâche le volant. Continuer ?")) != QMessageBox.Yes:
            return
        self.force.stop_all()
        self.b.save(ffb=True, odrive=odrive)

    def on_saved(self, store, ok, msg):
        if ok:
            self.settings.saved(store)
            self.statusBar().showMessage(T("Réglages volant/effets mémorisés") if store == "ffb"
                                         else T("Configuration ODrive mémorisée, la carte redémarre…"), 6000)
        else:
            QMessageBox.warning(self, T("Enregistrer"), T("Mémorisation refusée : {m}").format(m=msg))

    def reboot(self):
        if QMessageBox.question(self, T("Redémarrer la carte"),
                                T("Les réglages non mémorisés seront perdus et la carte refera son calage au "
                                  "démarrage (le volant bouge). Continuer ?")) != QMessageBox.Yes:
            return
        self.force.stop_all()
        self.b.request_state(P.IDLE)
        self.b.system("sr")

    def dfu(self):
        if QMessageBox.question(self, T("Mode DFU"),
                                T("La carte va quitter le mode volant et attendre un nouveau firmware "
                                  "(STM32CubeProgrammer, USB). Elle reviendra au firmware actuel après un "
                                  "débranchement/rebranchement si rien n'est flashé. Continuer ?")) != QMessageBox.Yes:
            return
        self.force.stop_all()
        self.b.request_state(P.IDLE)
        self.b.system("sd")

    # ------------------------------------------------------------ STOP
    def engage_estop(self):
        if not self.b.estop:
            self.toggle_estop()

    def toggle_estop(self):
        if not self.b.estop:
            self.force.stop_all()
            self.b.set_estop(True)
            return
        box = QMessageBox(self)
        box.setWindowTitle(T("Réarmer"))
        box.setText(T("Le moteur est au repos. Que faire ?"))
        b_arm = box.addButton(T("Réarmer et activer le moteur"), QMessageBox.AcceptRole)
        b_keep = box.addButton(T("Réarmer, moteur au repos"), QMessageBox.ActionRole)
        box.addButton(T("Garder le STOP"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is b_arm:
            self.b.set_estop(False, arm=True)
        elif box.clickedButton() is b_keep:
            self.b.set_estop(False, arm=False)

    def on_estop_changed(self, on):
        if on:
            self.force.stop_all()
            self.estop.setText(T("STOP VOLANT ENCLENCHÉ — RÉARMER"))
            self.estop.setObjectName("estopLatched")
        else:
            self.estop.setText(T("STOP VOLANT"))
            self.estop.setObjectName("estop")
        self.estop.style().unpolish(self.estop)
        self.estop.style().polish(self.estop)
        self._set_actions()

    def on_guard(self, speed):
        self.force.stop_all()
        what = (T("Le volant est sorti de la course réglée pendant un essai") if speed == float("inf")
                else T("Vitesse mesurée {v} °/s pendant un essai").format(v=f"{speed:+.0f}"))
        QMessageBox.critical(self, T("Coupure de sécurité"),
                             T("{what} : moteur mis au repos.\n\nCauses probables d'un emballement : calage du codeur "
                               "faux, CPR ou paires de pôles faux, courroie qui saute, parasites sur le codeur.\n"
                               "Le STOP reste enclenché : réarme-le quand le volant est sous contrôle.").format(what=what))

    # ------------------------------------------------------------ langue / fermeture
    def change_lang(self, _i):
        code = self.lang.currentData()
        if code == i18n.LANG:
            return
        i18n.save_lang(code)
        if QMessageBox.question(self, "SimForge Studio",
                                "Restart now to switch language?" if code == "en"
                                else "Redémarrer maintenant pour changer de langue ?") == QMessageBox.Yes:
            self.close()
            if getattr(sys, "frozen", False):
                QProcess.startDetached(sys.executable, sys.argv[1:])
            else:
                QProcess.startDetached(sys.executable, [os.path.abspath(sys.argv[0])] + sys.argv[1:])
            from PySide6.QtWidgets import QApplication
            QApplication.quit()

    def closeEvent(self, e):
        for tab in (self.monitor, self.joy):    # enregistrement CSV en cours : fermé proprement (données vidées)
            tab.b_log.setChecked(False)
        self.overlay.shutdown()
        self.force.stop_all()
        self.b.stop()
        self.pm.stop()
        self.sdl.shutdown()
        super().closeEvent(e)
