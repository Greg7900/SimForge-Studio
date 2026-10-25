"""Page Pédales › Firmware : flashe le firmware ChrGri fourni (PCB V6 ou bridge) avec esptool, sans autre logiciel."""
from __future__ import annotations

import io
import json
import os
import sys
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox,
                               QPlainTextEdit, QProgressBar, QMessageBox)

from . import i18n
from .i18n import T
from .theme import C
from .widgets import card, hint

try:
    import serial.tools.list_ports as _lp
except Exception:  # pragma: no cover
    _lp = None


def fw_root():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "firmware")


def images():
    """Firmwares livrés : dossiers firmware/<nom>/ avec manifest.json (offsets → fichiers)."""
    out = []
    root = fw_root()
    if not os.path.isdir(root):
        return out
    for d in sorted(os.listdir(root)):
        mf = os.path.join(root, d, "manifest.json")
        if os.path.isfile(mf):
            try:
                with open(mf, encoding="utf-8") as fh:
                    m = json.load(fh)
                m["dir"] = os.path.join(root, d)
                if all(os.path.isfile(os.path.join(m["dir"], f)) for _o, f in m["parts"]):
                    out.append(m)
            except Exception:
                pass
    out.sort(key=lambda m: m.get("order", 99))
    return out


def _loc(v):
    """Texte du manifeste dans la langue de l'interface."""
    if isinstance(v, dict):
        return v.get(i18n.LANG) or v.get("fr") or next(iter(v.values()), "")
    return v or ""


class _Out(io.TextIOBase):
    def __init__(self, cb):
        self.cb = cb
        self.buf = ""

    def write(self, s):
        self.buf += s
        while True:
            i = min([k for k in (self.buf.find("\n"), self.buf.find("\r")) if k >= 0], default=-1)
            if i < 0:
                break
            line, self.buf = self.buf[:i], self.buf[i + 1:]
            if line.strip():
                self.cb(line)
        return len(s)

    def flush(self):
        pass


class Flasher(QObject):
    line = Signal(str)
    progress = Signal(int)
    done = Signal(bool, str)

    def run(self, port, img, erase):
        threading.Thread(target=self._run, args=(port, img, erase), daemon=True).start()

    def _emit(self, s):
        self.line.emit(s)
        if "%" in s and "riting" in s:            # « Writing at 0x… (45 %) » ou « … 45.2% … » selon la version
            import re
            m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
            if m:
                self.progress.emit(int(float(m.group(1))))

    def _run(self, port, img, erase):
        try:
            import esptool
        except Exception:
            self.done.emit(False, T("Le module esptool manque : installe-le (pip install esptool) ou relance "
                                    "« SimForge Studio V3.bat » qui l'installe."))
            return
        parts = []
        for off, f in img["parts"]:
            parts += [off, os.path.join(img["dir"], f)]
        try:
            v5 = int(str(esptool.__version__).split(".")[0]) >= 5
        except Exception:
            v5 = False
        h = (lambda x: x.replace("_", "-")) if v5 else (lambda x: x)   # esptool 5 : noms avec tirets
        # 921600 bauds, puis 115200 si ça échoue (câble long, pilote CH343 capricieux à haute vitesse)
        for baud in ("921600", "115200"):
            if baud != "921600":
                self._emit(T("Nouvel essai à {b} bauds…").format(b=baud) + "\n")
            args = ["--chip", img.get("chip", "esp32s3"), "--port", port, "--baud", baud,
                    "--before", h("default_reset"), "--after", h("hard_reset"), h("write_flash")]
            if erase:
                args.append("--erase-all")
            args += ["-z"] + parts
            ok, msg = self._esptool(esptool, args)
            if ok:
                break
        self.done.emit(ok, msg)

    def _esptool(self, esptool, args):
        out = _Out(self._emit)
        old = sys.stdout, sys.stderr
        ok, msg = False, ""
        try:
            sys.stdout = sys.stderr = out
            esptool.main(args)
            ok = True
        except SystemExit as e:
            ok = e.code in (0, None)
            msg = "" if ok else str(e)
        except BaseException as e:  # FatalError, SerialException…
            msg = str(e)
        finally:
            out.write("\n")
            sys.stdout, sys.stderr = old
        return ok, msg


class PedalFirmwareTab(QWidget):
    def __init__(self, mgr, parent=None):
        super().__init__(parent)
        self.m = mgr
        self.port = None
        self.f = Flasher()
        self.f.line.connect(self._line)
        self.f.progress.connect(lambda v: self.bar.setValue(v))
        self.f.done.connect(self._done)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 8)
        root.setSpacing(12)

        c, l = card(T("Flasher le firmware des pédales"))
        l.addWidget(hint(T("Firmware open source de ChrGri (DIY-Sim-Racing-FFB-Pedal), compilé pour ton PCB V6 et "
                           "compatible avec SimForge. Fais une pédale à la fois. Tes réglages enregistrés sont "
                           "conservés si la version de configuration ne change pas ; sinon la pédale repart des "
                           "valeurs par défaut.")))
        r = QHBoxLayout()
        r.addWidget(QLabel(T("Firmware")))
        self.img = QComboBox()
        self.img.setMinimumWidth(360)
        for m in images():
            self.img.addItem(_loc(m.get("label")) or os.path.basename(m["dir"]), m)
        r.addWidget(self.img)
        r.addStretch()
        l.addLayout(r)
        self.img_info = hint("")
        l.addWidget(self.img_info)
        self.img.currentIndexChanged.connect(self._img)
        r = QHBoxLayout()
        r.addWidget(QLabel(T("Port")))
        self.port_cb = QComboBox()
        self.port_cb.setMinimumWidth(360)
        r.addWidget(self.port_cb)
        b = QPushButton(T("Actualiser"))
        b.clicked.connect(self._ports)
        r.addWidget(b)
        r.addStretch()
        l.addLayout(r)
        self.erase = QCheckBox(T("Tout effacer avant (efface aussi les réglages enregistrés)"))
        l.addWidget(self.erase)
        r = QHBoxLayout()
        self.go = QPushButton(T("Flasher"))
        self.go.setObjectName("primary")
        self.go.clicked.connect(self.flash)
        r.addWidget(self.go)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        r.addWidget(self.bar, 1)
        l.addLayout(r)
        self.res = QLabel("")
        self.res.setWordWrap(True)
        l.addWidget(self.res)
        root.addWidget(c)

        c, l = card(T("Si le flashage n'arrive pas à se connecter"))
        l.addWidget(hint(T("1. Ferme SimHub (il garde le port ouvert).\n"
                           "2. Utilise le port USB de la carte relié à la puce série (CH343/CP210x).\n"
                           "3. Maintiens le bouton BOOT de l'ESP32, appuie puis relâche RESET, relâche BOOT, "
                           "puis clique de nouveau sur « Flasher ».")))
        root.addWidget(c)
        self.log = QPlainTextEdit()
        self.log.setObjectName("console")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        root.addWidget(self.log, 1)
        c, l = card(T("Licence"))
        l.addWidget(hint(T("Firmware : ChrGri et contributeurs, DIY-Sim-Racing-FFB-Pedal, licence CC BY-NC-SA 4.0 "
                           "(usage non commercial, partage dans les mêmes conditions). Voir firmware/LICENSE.txt.")))
        root.addWidget(c)
        self._img()
        self._ports()
        self.m.changed.connect(self._ports)

    def _img(self, *_):
        m = self.img.currentData()
        if not m:
            self.img_info.setText(T("Aucun firmware trouvé dans le dossier « firmware » de SimForge."))
            self.go.setEnabled(False)
            return
        self.go.setEnabled(True)
        self.img_info.setText(_loc(m.get("info")))

    def _ports(self, *_):
        cur = self.port_cb.currentData()
        self.port_cb.clear()
        if _lp is None:
            return
        ped = {p.port: p.name for p in self.m.pedals()}
        for p in sorted(_lp.comports(), key=lambda p: p.device):
            if p.vid is None or (p.vid, p.pid) == (0x1209, 0x0D40):
                continue                      # ignore le volant
            name = ped.get(p.device)
            txt = f"{p.device} — " + (name or (p.description or ""))
            self.port_cb.addItem(txt, p.device)
        i = self.port_cb.findData(cur)
        if i >= 0:
            self.port_cb.setCurrentIndex(i)

    def flash(self):
        port, img = self.port_cb.currentData(), self.img.currentData()
        if not port or not img:
            QMessageBox.information(self, T("Flasher"), T("Choisis un port."))
            return
        # port USB natif d'une pédale en marche (firmware « un câble ») : esptool ne sait pas la mettre en mode
        # flashage par là (seul le mode flashage de la puce, PID 0x1001, le permet)
        ports = _lp.comports() if _lp else []
        native = any(p.device == port and p.vid == 0x303A and p.pid != 0x1001 for p in ports)
        if native and QMessageBox.question(self, T("Flasher"), T(
                "{p} est le port USB natif de la pédale : le flashage par ce port échoue en général. Branche le "
                "câble sur le port UART (puce CH343) et choisis ce port-là. Essayer quand même ?").format(p=port)) \
                != QMessageBox.Yes:
            return
        if QMessageBox.question(self, T("Flasher"), T("Flasher « {f} » sur {p} ?\nNe débranche pas la pédale "
                                                      "pendant le flashage.").format(f=_loc(img.get("label")), p=port)) \
                != QMessageBox.Yes:
            return
        self.port = port
        self.m.release(port)
        self.go.setEnabled(False)
        self.bar.setValue(0)
        self.res.setText(T("Flashage en cours…"))
        self.res.setStyleSheet("")
        self.log.clear()
        self.f.run(port, img, self.erase.isChecked())

    def _line(self, s):
        self.log.appendPlainText(s)

    def _done(self, ok, msg):
        self.go.setEnabled(True)
        if self.port:
            self.m.unpause(self.port)
        if ok:
            self.bar.setValue(100)
            self.res.setText(T("Terminé. La pédale redémarre ; elle réapparaît dans Pédales › Réglages."))
            self.res.setStyleSheet(f"color: {C['ok']};")
        else:
            self.res.setText(T("Échec : {m}").format(m=msg or T("voir le journal ci-dessous")) + "\n" +
                             T("Essaie la manipulation BOOT/RESET ci-dessous."))
            self.res.setStyleSheet(f"color: {C['bad']};")
