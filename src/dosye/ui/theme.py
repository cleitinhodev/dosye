"""Dosye visual theme — colours taken from the app icon (night-sky indigo folder,
violet glow, golden crescent moon, warm mascot brown) — and the global stylesheet."""
from PySide6.QtGui import QColor

from ..paths import asset

# Night sky
BG0 = "#070920"      # window background (darkest)
BG1 = "#0D1032"      # side panels
BG2 = "#141848"      # cards / sections
BG3 = "#1B2060"      # inputs, buttons
BG4 = "#232A78"      # hover
LINE = "#252B6C"
LINE2 = "#363E98"
TEXT = "#ECEBFF"
MUTED = "#A3A7DA"
DIM = "#7076AE"
# Folder gradient + neon
INDIGO = "#4C46F0"
VIOLET = "#8B5CFF"
BLUE = "#3D6BFF"
CYAN = "#6FC3FF"
# Moon + mascot
GOLD = "#FFC93C"
GOLD_LIGHT = "#FFE38A"
BROWN = "#B7794A"
PINK = "#FF7EB3"

# Quick palette shown in the Fill section (first row echoes the icon)
PALETTE = ["#3F3FE0", "#6A4CFF", "#8B5CFF", "#3D6BFF", "#6FC3FF", "#FFC93C", "#B7794A", "#F7B733",
           "#FF8A3D", "#F43F5E", "#FF7EB3", "#C084FC", "#2DD4BF", "#22C55E", "#94A3B8", "#1E1B4B"]


def qcol(c, a=None):
    q = QColor(c)
    if a is not None:
        q.setAlphaF(max(0.0, min(1.0, a)))
    return q


def stylesheet(fonts, intensity=0.7, glow=True):
    """Builds the application stylesheet. intensity (0..1) scales neon/gradient strength."""
    k = max(0.0, min(1.0, intensity))
    fam = ", ".join(f'"{f}"' for f in fonts) + ", sans-serif"
    ui = asset("ui").replace("\\", "/")
    a_sel = int(120 + 100 * k)                    # selected border alpha
    neon = f"rgba(139, 92, 255, {a_sel})"
    gold_line = f"rgba(255, 201, 60, {int(90 + 120 * k)})"
    focus = f"rgba(160, 130, 255, {int(150 + 100 * k)})" if glow else "#5A55C8"
    return f"""
* {{ font-family: {fam}; font-size: 10pt; color: {TEXT}; }}
QMainWindow {{ background: {BG0}; }}
#root {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #080A26, stop:0.55 #0A0C2C, stop:1 #120A33); }}
#sidebar, #panel {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0F1338, stop:1 #0B0E2C);
    border: 1px solid {LINE}; border-radius: 18px; }}
#sectionTitle {{ font-size: 10.5pt; font-weight: 700; color: #FFFFFF; }}
#sectionCard {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #161B4E, stop:1 #12163F);
    border: 1px solid {LINE}; border-radius: 14px; }}
#hint {{ color: {DIM}; font-size: 8.8pt; }}
#valueLabel {{ color: {GOLD_LIGHT}; font-size: 9pt; }}
#rowLabel {{ color: {MUTED}; }}
#count {{ color: {GOLD_LIGHT}; font-size: 8.6pt; background: rgba(255, 201, 60, 0.10);
    border: 1px solid rgba(255, 201, 60, 0.28); border-radius: 9px; padding: 1px 8px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {LINE2}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {VIOLET}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
QPushButton {{ background: {BG3}; border: 1px solid {LINE2}; border-radius: 10px; padding: 7px 12px; }}
QPushButton:hover {{ background: {BG4}; border-color: {neon}; }}
QPushButton:pressed {{ background: #161A50; }}
QPushButton:disabled {{ color: #565C92; border-color: {LINE}; }}
QPushButton:focus {{ outline: none; border-color: {focus}; }}
QPushButton#primary {{ border: 1px solid rgba(255,255,255,0.18); color: white; font-weight: 700; font-size: 10.5pt; padding: 11px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4C46F0, stop:0.6 #7552FF, stop:1 #9D5CFF); }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5A55FF, stop:0.6 #8463FF, stop:1 #AD70FF);
    border-color: {gold_line}; }}
QPushButton#gold {{ color: #2A1A00; font-weight: 700; border: 1px solid rgba(255, 240, 190, 0.6);
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFE38A, stop:1 #FFB82E); }}
QPushButton#gold:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFF0B0, stop:1 #FFC54A); }}
QPushButton#seg, QPushButton#chip {{ background: #161A4C; border: 1px solid {LINE}; padding: 6px 4px; border-radius: 9px; color: {MUTED}; }}
QPushButton#chip {{ font-size: 8.5pt; padding: 4px 2px; }}
QPushButton#seg:hover, QPushButton#chip:hover {{ color: {TEXT}; border-color: {LINE2}; background: #1C2160; }}
QPushButton#seg:checked, QPushButton#chip:checked {{ color: #FFFFFF; font-weight: 600; border: 1px solid {neon};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3A33C8, stop:1 #5B3FD8); }}
QPushButton#ghost {{ background: rgba(20, 24, 72, 0.55); border: 1px solid rgba(160, 150, 255, 0.22); }}
QPushButton#ghost:hover {{ background: rgba(60, 54, 170, 0.55); border-color: {neon}; }}
QPushButton#iconbtn {{ background: rgba(20, 24, 72, 0.55); border: 1px solid rgba(160, 150, 255, 0.22); padding: 7px; border-radius: 10px; }}
QPushButton#iconbtn:hover {{ background: rgba(60, 54, 170, 0.6); border-color: {neon}; }}
QPushButton#heart {{ background: rgba(255, 126, 179, 0.12); border: 1px solid rgba(255, 126, 179, 0.45); color: #FFD3E6; font-weight: 600; }}
QPushButton#heart:hover {{ background: rgba(255, 126, 179, 0.25); border-color: #FF9BC6; }}
QPushButton#sticker {{ background: #12164A; border: 1px solid {LINE}; border-radius: 10px; padding: 4px; }}
QPushButton#sticker:hover {{ border-color: {GOLD}; background: #1B2060; }}
QPushButton#swatch {{ border-radius: 11px; padding: 0; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; }}
QPushButton#link {{ background: transparent; border: none; color: {CYAN}; text-align: left; padding: 2px; }}
QPushButton#link:hover {{ color: {GOLD_LIGHT}; text-decoration: underline; }}
QSlider {{ min-height: 18px; }}
QSlider::groove:horizontal {{ height: 4px; background: #232966; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4C46F0, stop:1 #A06BFF); border-radius: 2px; }}
QSlider::handle:horizontal {{ background: qradialgradient(cx:0.5, cy:0.4, radius:0.6, fx:0.5, fy:0.3, stop:0 #FFF3C4, stop:1 #FFC93C);
    width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; border: 2px solid #8B5CFF; }}
QSlider::handle:horizontal:hover {{ border-color: {GOLD_LIGHT}; }}
QSlider::sub-page:horizontal:disabled {{ background: #2A2F66; }}
QSlider::handle:horizontal:disabled {{ border-color: #3A4080; background: #6D72A6; }}
QCheckBox {{ spacing: 8px; color: {MUTED}; }}
QCheckBox:hover {{ color: {TEXT}; }}
QCheckBox::indicator {{ width: 38px; height: 20px; border: none; background: transparent; image: url({ui}/toggle_off.png); }}
QCheckBox::indicator:checked {{ image: url({ui}/toggle_on.png); }}
QCheckBox::indicator:disabled {{ image: url({ui}/toggle_off_dis.png); }}
QCheckBox::indicator:checked:disabled {{ image: url({ui}/toggle_on_dis.png); }}
QCheckBox:disabled {{ color: #565C92; }}
QCheckBox#plain::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {LINE2}; background: #12164A; image: none; }}
QCheckBox#plain::indicator:checked {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4C46F0, stop:1 #9D5CFF); border-color: {neon}; }}
QLineEdit {{ background: #11154A; border: 1px solid {LINE2}; border-radius: 10px; padding: 6px 10px;
    selection-background-color: #5B3FD8; }}
QLineEdit:focus {{ border: 1px solid {focus}; background: #141950; }}
QComboBox {{ background: {BG3}; border: 1px solid {LINE2}; border-radius: 9px; padding: 5px 10px; }}
QComboBox:hover {{ border-color: {neon}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url({ui}/chevron.png); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{ background: #12164A; border: 1px solid {LINE2}; selection-background-color: #3A33C8; outline: none; padding: 4px; }}
QToolTip {{ background: #161A50; color: {TEXT}; border: 1px solid {LINE2}; padding: 6px; border-radius: 6px; }}
QDialog, QMessageBox {{ background: #0C0F30; }}
QTextBrowser {{ background: transparent; border: none; }}
QTabWidget::pane {{ border: none; }}
#toast {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(36, 34, 120, 240), stop:1 rgba(70, 44, 150, 240));
    border: 1px solid rgba(255, 201, 60, 0.55); border-radius: 14px; }}
#toastText {{ color: #FFFFFF; font-weight: 600; }}
#toastPath {{ color: {MUTED}; font-size: 8.6pt; }}
#dlgTitle {{ font-size: 15pt; font-weight: 800; color: #FFFFFF; }}
#dlgSub {{ color: {MUTED}; }}
"""
