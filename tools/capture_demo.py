"""Capture d'écran d'une page de SimForge Studio en mode démo (matériel simulé), sans afficher de fenêtre.

    python tools/capture_demo.py p_settings capture.png          # page Pédales › Réglages, en français
    python tools/capture_demo.py w_settings capture.png --lang en

Clés de page : overview, w_setup, w_settings, w_monitor, w_encoder, w_force, p_settings, p_fw,
t_joy, t_overlay, t_console, t_log (voir le menu dans simforge/app.py).
Sert à vérifier une page modifiée sans volant ni pédales branchés.
"""
import argparse
import os
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "simforge-studio-v3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page", nargs="?", default="overview")
    ap.add_argument("out", nargs="?", default="capture.png")
    ap.add_argument("--lang", default="fr", choices=("fr", "en"))
    ap.add_argument("--wait", type=float, default=3.0, help="secondes avant la capture (données simulées)")
    ap.add_argument("--size", default="1500x1000")
    args = ap.parse_args()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, str(APP))
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from simforge import i18n
    i18n.LANG = args.lang            # avant d'importer les onglets
    from simforge.app import MainWindow
    from simforge.theme import QSS
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    win = MainWindow(demo=True)
    w, h = (int(v) for v in args.size.split("x"))
    win.resize(w, h)
    win.show()
    win.goto(args.page)

    def shot():
        win.grab().save(args.out)
        print("capture :", os.path.abspath(args.out))
        os._exit(0)                   # sortie immédiate : les threads de démo tournent encore

    QTimer.singleShot(int(args.wait * 1000), shot)
    app.exec()


if __name__ == "__main__":
    main()
