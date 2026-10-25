"""Tests SimForge Studio : sans matériel, Qt hors écran.

    pip install -r simforge-studio-v3/requirements.txt pytest
    python -m pytest tests
"""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "simforge-studio-v3"))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
