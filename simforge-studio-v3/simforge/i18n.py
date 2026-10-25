"""Traduction FR/EN. Le texte source est en français ; l'anglais est la langue par défaut.

La langue est lue au démarrage (avant l'import des onglets) ; changer de langue relance l'appli.
"""
from __future__ import annotations

LANG = "en"
LANGS = {"en": "English", "fr": "Français"}


def settings():
    """Préférences de l'appli (registre Windows), partagées par toutes les pages."""
    from PySide6.QtCore import QSettings
    return QSettings("SimForge", "SimForge Studio V3")


def load_lang() -> str:
    global LANG
    try:
        v = str(settings().value("lang", "en"))
        LANG = v if v in LANGS else "en"
    except Exception:
        LANG = "en"
    return LANG


def save_lang(lang: str):
    settings().setValue("lang", lang)


def T(fr: str) -> str:
    if LANG == "fr":
        return fr
    return EN.get(fr, fr)


from .i18n_en import EN  # noqa: E402
