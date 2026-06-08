from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class SensorCard(QWidget):
    def __init__(self, title: str, unit: str = "", parent=None):
        super().__init__(parent)
        self.unit = unit
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(4)
        
        # Stylesheet for card container
        self.setStyleSheet("""
            SensorCard {
                background-color: #1a1a1e;
                border: 1px solid #2d2d34;
                border-radius: 8px;
            }
        """)
        
        # Title
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        self.layout.addWidget(self.lbl_title)
        
        # Large Value
        self.lbl_value = QLabel("N/A")
        self.lbl_value.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: 700;")
        self.layout.addWidget(self.lbl_value)
        
        # Status text
        self.lbl_status = QLabel("Inactive")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
        self.layout.addWidget(self.lbl_status)

    def update_value(self, value: Any, status: str = "ok", status_text: str = ""):
        """Updates the numeric/string value of the card and updates the alarm indicator."""
        # Value string format
        if isinstance(value, float):
            val_str = f"{value:.2f} {self.unit}".strip()
        else:
            val_str = f"{value} {self.unit}".strip()
            
        self.lbl_value.setText(val_str)
        
        # Color styling based on status level
        if status.lower() == "ok":
            self.lbl_status.setText(status_text if status_text else "STATUS: OK")
            self.lbl_status.setStyleSheet("color: #00b4d8; font-size: 11px; font-weight: 500;")
        elif status.lower() == "warning":
            self.lbl_status.setText(status_text if status_text else "STATUS: WARNING")
            self.lbl_status.setStyleSheet("color: #ff9f1c; font-size: 11px; font-weight: 500;")
        elif status.lower() == "error":
            self.lbl_status.setText(status_text if status_text else "STATUS: ERROR")
            self.lbl_status.setStyleSheet("color: #e63946; font-size: 11px; font-weight: 500;")
        else:
            self.lbl_status.setText(status_text if status_text else "Inactive")
            self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
