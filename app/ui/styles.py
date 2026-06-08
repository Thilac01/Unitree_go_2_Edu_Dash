# Modern Dark QSS Stylesheet for DASH Ground Station

ACCENT_COLOR = "#00b4d8"      # Neon Cyan
WARNING_COLOR = "#ff9f1c"     # Amber Warning
CRITICAL_COLOR = "#e63946"    # Danger / E-Stop Red
BG_DARK = "#121214"           # Deep Slate Black
BG_PANEL = "#1a1a1e"          # Surface gray
BORDER_COLOR = "#2d2d34"      # Subtle boundary border
TEXT_COLOR = "#e2e8f0"        # Off-white readability
TEXT_DIM = "#94a3b8"          # Slate grey subheadings

QSS_DARK_STYLE = f"""
/* Global Window Styling */
QMainWindow {{
    background-color: {BG_DARK};
    color: {TEXT_COLOR};
}}

QWidget {{
    font-family: 'Segoe UI', -apple-system, Roboto, Helvetica, sans-serif;
    font-size: 13px;
    color: {TEXT_COLOR};
}}

/* Sidebar and Workspace layout splitters */
QSplitter::handle {{
    background-color: {BORDER_COLOR};
}}

/* Dock Widgets */
QDockWidget {{
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
    border: 1px solid {BORDER_COLOR};
}}

QDockWidget::title {{
    background: {BG_PANEL};
    padding-left: 10px;
    padding-top: 6px;
    padding-bottom: 6px;
    font-weight: bold;
    color: {TEXT_COLOR};
    border-bottom: 1px solid {BORDER_COLOR};
}}

/* Toolbars */
QToolBar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER_COLOR};
    spacing: 12px;
    padding: 8px;
}}

QToolBar QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
    color: {TEXT_COLOR};
    font-weight: 600;
}}

QToolBar QToolButton:hover {{
    background-color: {BORDER_COLOR};
    border: 1px solid {ACCENT_COLOR};
}}

/* Left Sidebar Menu List */
QListWidget {{
    background-color: {BG_PANEL};
    border: none;
    border-right: 1px solid {BORDER_COLOR};
    outline: 0;
}}

QListWidget::item {{
    padding: 12px 16px;
    margin: 2px 6px;
    border-radius: 6px;
    color: {TEXT_DIM};
    font-weight: 500;
}}

QListWidget::item:hover {{
    background-color: {BORDER_COLOR};
    color: {TEXT_COLOR};
}}

QListWidget::item:selected {{
    background-color: #00b4d8;
    color: #121214;
    font-weight: bold;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {BG_DARK};
    width: 10px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_COLOR};
    min-height: 20px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ACCENT_COLOR};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {BG_DARK};
    height: 10px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER_COLOR};
    min-width: 20px;
    border-radius: 5px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* GroupBoxes & Panels */
QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 16px;
    font-weight: bold;
    color: {ACCENT_COLOR};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    color: {TEXT_COLOR};
}}

/* Buttons */
QPushButton {{
    background-color: {BORDER_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 8px 16px;
    color: {TEXT_COLOR};
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: #24242b;
    border-color: {ACCENT_COLOR};
}}

QPushButton:pressed {{
    background-color: {ACCENT_COLOR};
    color: {BG_DARK};
}}

QPushButton:disabled {{
    background-color: #1c1c20;
    color: #4b5563;
    border-color: #1c1c20;
}}

/* Specific Accent Buttons */
QPushButton#btn_connect, QPushButton#btn_start_slam, QPushButton#btn_fix, QPushButton#btn_save {{
    background-color: {ACCENT_COLOR};
    color: {BG_DARK};
    border: 1px solid {ACCENT_COLOR};
}}

QPushButton#btn_connect:hover, QPushButton#btn_start_slam:hover, QPushButton#btn_fix:hover, QPushButton#btn_save:hover {{
    background-color: #00d2ff;
}}

QPushButton#btn_estop {{
    background-color: {CRITICAL_COLOR};
    color: white;
    font-weight: bold;
    font-size: 14px;
    border: 1px solid {CRITICAL_COLOR};
    border-radius: 6px;
}}

QPushButton#btn_estop:hover {{
    background-color: #ef4444;
}}

/* Input LineEdits & SpinBoxes */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_DARK};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 12px;
    color: {TEXT_COLOR};
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT_COLOR};
}}

QComboBox::drop-down {{
    border: none;
    background-color: transparent;
}}

/* Table Headers & Items */
QTableWidget, QTreeView {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_COLOR};
    gridline-color: {BORDER_COLOR};
    border-radius: 6px;
}}

QHeaderView::section {{
    background-color: {BG_DARK};
    color: {TEXT_DIM};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {BORDER_COLOR};
    font-weight: bold;
}}

QTableWidget::item {{
    padding: 6px;
}}

QTableWidget::item:selected {{
    background-color: {BORDER_COLOR};
    color: {ACCENT_COLOR};
}}

/* TabBar styling for multi-tabs (like the SSH console) */
QTabWidget::pane {{
    border: 1px solid {BORDER_COLOR};
    background-color: {BG_PANEL};
    border-radius: 6px;
}}

QTabBar::tab {{
    background: {BG_DARK};
    border: 1px solid {BORDER_COLOR};
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {TEXT_DIM};
}}

QTabBar::tab:selected, QTabBar::tab:hover {{
    background: {BG_PANEL};
    color: {TEXT_COLOR};
    border-bottom-color: transparent;
}}

QTabBar::tab:selected {{
    border-top: 2px solid {ACCENT_COLOR};
    font-weight: bold;
}}

/* Text browser / logger boxes */
QTextBrowser, QTextEdit {{
    background-color: #0b0b0d;
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    color: {TEXT_COLOR};
    font-family: Consolas, 'Courier New', monospace;
}}

/* Statusbar */
QStatusBar {{
    background-color: {BG_PANEL};
    border-top: 1px solid {BORDER_COLOR};
    color: {TEXT_DIM};
}}
"""
