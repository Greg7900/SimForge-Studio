"""Thème visuel : panneau d'instrument sombre, accent ambre, rouge réservé au STOP."""

C = {
    "bg": "#15171a",
    "panel": "#1d2024",
    "panel2": "#24282d",
    "line": "#33383f",
    "text": "#e6e8eb",
    "dim": "#8b929b",
    "accent": "#f2a93b",      # ambre : valeurs modifiées, focus
    "accent_dim": "#7a5520",
    "ok": "#4cc38a",
    "warn": "#f2c94c",
    "bad": "#e5484d",
    "blue": "#5aa9f2",
}

MONO = "Consolas, 'Cascadia Mono', 'DejaVu Sans Mono', monospace"
SANS = "'Segoe UI', 'Noto Sans', 'DejaVu Sans', sans-serif"

QSS = f"""
* {{ font-family: {SANS}; font-size: 10pt; color: {C['text']}; }}
QMainWindow, QWidget#root {{ background: {C['bg']}; }}
QWidget {{ background: transparent; }}
QToolTip {{ background: {C['panel2']}; color: {C['text']}; border: 1px solid {C['line']}; padding: 4px; }}

QFrame#card {{ background: {C['panel']}; border: 1px solid {C['line']}; border-radius: 6px; }}
QLabel#cardTitle {{ color: {C['dim']}; font-size: 8.5pt; font-weight: 600; letter-spacing: 1.5px; }}
QLabel#hint {{ color: {C['dim']}; font-size: 9pt; }}
QLabel#warnText {{ color: {C['warn']}; }}
QLabel#bigValue {{ font-family: {MONO}; font-size: 22pt; font-weight: 600; }}
QLabel#midValue {{ font-family: {MONO}; font-size: 13pt; }}
QLabel#unit {{ color: {C['dim']}; font-size: 9pt; }}
QLabel#brand {{ font-size: 13pt; font-weight: 700; letter-spacing: 3px; }}
QLabel#brandSub {{ color: {C['accent']}; font-size: 13pt; font-weight: 300; letter-spacing: 3px; }}
QLabel#badge {{ background: {C['accent_dim']}; color: {C['accent']}; border-radius: 3px; padding: 1px 6px; font-size: 8pt; font-weight: 700; }}

QTabWidget::pane {{ border: none; border-top: 1px solid {C['line']}; }}
QTabBar::tab {{ background: transparent; color: {C['dim']}; padding: 9px 18px; border: none;
               border-bottom: 2px solid transparent; font-weight: 600; }}
QTabBar::tab:selected {{ color: {C['text']}; border-bottom: 2px solid {C['accent']}; }}
QTabBar::tab:hover {{ color: {C['text']}; }}

QPushButton {{ background: {C['panel2']}; border: 1px solid {C['line']}; border-radius: 4px; padding: 6px 12px; }}
QPushButton:hover {{ border-color: {C['dim']}; }}
QPushButton:pressed {{ background: {C['line']}; }}
QPushButton:disabled {{ color: {C['dim']}; border-color: {C['panel2']}; }}
QPushButton:checked {{ background: {C['accent_dim']}; border-color: {C['accent']}; color: {C['accent']}; }}
QPushButton#primary {{ background: {C['accent']}; color: #1a1205; border: none; font-weight: 700; }}
QPushButton#primary:disabled {{ background: {C['accent_dim']}; color: {C['panel']}; }}
QPushButton#danger {{ background: transparent; color: {C['bad']}; border: 1px solid {C['bad']}; }}
QPushButton#estop {{ background: {C['bad']}; color: white; border: 2px solid #ff8a8d; border-radius: 6px;
                     font-size: 13pt; font-weight: 800; letter-spacing: 2px; padding: 6px 22px; }}
QPushButton#estop:hover {{ background: #f05a5f; }}
QPushButton#estopLatched {{ background: #3a1416; color: {C['bad']}; border: 2px solid {C['bad']}; border-radius: 6px;
                     font-size: 11pt; font-weight: 800; letter-spacing: 1px; padding: 6px 16px; }}

QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QPlainTextEdit {{
    background: {C['bg']}; border: 1px solid {C['line']}; border-radius: 4px; padding: 3px 6px;
    selection-background-color: {C['accent_dim']}; }}
QSpinBox, QDoubleSpinBox {{ font-family: {MONO}; }}
QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QComboBox:focus {{ border-color: {C['accent']}; }}
QSpinBox[modified="true"], QDoubleSpinBox[modified="true"], QComboBox[modified="true"] {{
    border-color: {C['accent']}; color: {C['accent']}; }}
QCheckBox[modified="true"] {{ color: {C['accent']}; }}
QComboBox QAbstractItemView {{ background: {C['panel2']}; border: 1px solid {C['line']}; selection-background-color: {C['accent_dim']}; }}
QPlainTextEdit#console {{ font-family: {MONO}; font-size: 9.5pt; background: #0f1113; }}

QSlider::groove:horizontal {{ height: 4px; background: {C['line']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {C['dim']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {C['text']}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}
QSlider[modified="true"]::sub-page:horizontal {{ background: {C['accent']}; }}
QSlider[modified="true"]::handle:horizontal {{ background: {C['accent']}; }}

QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {C['dim']}; border-radius: 3px; background: {C['bg']}; }}
QCheckBox::indicator:checked {{ background: {C['accent']}; border-color: {C['accent']}; }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {C['line']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QTableWidget {{ background: {C['bg']}; gridline-color: {C['line']}; border: 1px solid {C['line']}; font-family: {MONO}; }}
QHeaderView::section {{ background: {C['panel2']}; color: {C['dim']}; border: none; padding: 4px; }}
QStatusBar {{ background: {C['panel']}; color: {C['dim']}; border-top: 1px solid {C['line']}; }}
QGroupBox {{ border: 1px solid {C['line']}; border-radius: 4px; margin-top: 10px; padding-top: 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; color: {C['dim']}; }}
"""
