"""Tema visual global del IDE URON (Estilo Dark Pro)."""
from PyQt6.QtGui import QColor

BG_MAIN       = "#1e1e1e"  
BG_PANEL      = "#252526"  
BG_INPUT      = "#3c3c3c"  
BORDER        = "#3e3e42"  
TEXT_MAIN     = "#cccccc"  
TEXT_MUTED    = "#858585"  
ACCENT_BLUE   = "#007acc"  
ACCENT_GREEN  = "#2ecc71"  
ACCENT_RED    = "#e74c3c"  

STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {BG_MAIN};
    color: {TEXT_MAIN};
}}
QDockWidget {{
    color: {TEXT_MAIN};
    font-weight: bold;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background: {BG_PANEL};
    padding: 6px;
    border-bottom: 1px solid {BORDER};
}}
QWidget {{
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 13px;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 3px;
    color: {TEXT_MAIN};
}}
QPushButton {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 5px 10px;
    color: {TEXT_MAIN};
}}
QPushButton:hover {{ background-color: #4a4a4a; }}
QPushButton:pressed {{ background-color: {ACCENT_BLUE}; }}
QTreeWidget, QListWidget, QTableView {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    outline: none;
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {ACCENT_BLUE};
    color: white;
}}
QHeaderView::section {{
    background-color: {BG_MAIN};
    border: none;
    padding: 4px;
}}
QScrollBar:vertical {{
    border: none;
    background: {BG_PANEL};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: #424242;
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QMenuBar {{ background-color: {BG_MAIN}; }}
QMenuBar::item:selected {{ background-color: {BG_INPUT}; }}
QMenu {{ background-color: {BG_PANEL}; border: 1px solid {BORDER}; }}
QMenu::item:selected {{ background-color: {ACCENT_BLUE}; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; }}
QTabBar::tab {{ background: {BG_PANEL}; padding: 6px 12px; border: 1px solid {BORDER}; }}
QTabBar::tab:selected {{ background: {BG_MAIN}; border-bottom-color: {BG_MAIN}; }}
"""