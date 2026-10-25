"""SimForge Studio V3 — wheel (Odrive-Wheel, ODrive 0.5.6 + OpenFFBoard effects) and ChrGri active pedals in one app.

    python simforge_studio.py          # real wheel
    python simforge_studio.py --demo   # simulated board (no hardware)
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
LOG = (Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent) / "errors.log"


def _install_crash_handler():
    """Started without a console (pythonw/exe): log errors to errors.log and show them."""
    import traceback

    def hook(exc_type, exc, tb):
        txt = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(txt + "\n")
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QMessageBox, QApplication
            if QApplication.instance():
                QMessageBox.critical(None, "SimForge Studio — error", f"{exc_type.__name__}: {exc}\n\n{LOG}")
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def main():
    _install_crash_handler()
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="simulated wheel")
    args = ap.parse_args()
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("simforge.studio.v3")
        except Exception:
            pass
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("SimForge Studio V3")
    # la langue doit être fixée AVANT d'importer les onglets
    from simforge import i18n
    i18n.load_lang()
    if i18n.LANG == "fr":  # boutons standard Qt (Oui / Non / Annuler…)
        from PySide6.QtCore import QTranslator, QLibraryInfo
        tr = QTranslator(app)
        if tr.load("qtbase_fr", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            app.installTranslator(tr)
    from simforge.app import MainWindow
    from simforge.theme import QSS
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    icon = HERE / "simforge_studio.png"
    win = MainWindow(demo=args.demo, icon_path=str(icon) if icon.exists() else None)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
