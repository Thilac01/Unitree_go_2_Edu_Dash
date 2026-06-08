import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QTextBrowser, QLineEdit, QLabel, QGroupBox, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor

class QLogHandler(logging.Handler):
    """Interceptors to catch standard python logging calls and forward them to PyQt5 signals."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        log_entry = self.format(record)
        self.callback(record.levelname, log_entry)

class TabLogging(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title
        self.layout.addWidget(QLabel("<h2>Central Diagnostic Logging System</h2>"))
        
        # Filters Toolbar
        self.filter_layout = QHBoxLayout()
        
        self.filter_layout.addWidget(QLabel("Channel:"))
        self.combo_channel = QComboBox()
        self.combo_channel.addItems(["DASH Application", "Robot System (journalctl)", "ROS2 Nodes Diagnostics", "SLAM Mapping Logs"])
        self.filter_layout.addWidget(self.combo_channel)
        
        self.filter_layout.addWidget(QLabel("Min Level:"))
        self.combo_level = QComboBox()
        self.combo_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.combo_level.setCurrentIndex(1) # default INFO
        self.combo_level.currentIndexChanged.connect(self.refresh_log_display)
        self.filter_layout.addWidget(self.combo_level)
        
        self.filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter text...")
        self.search_input.textChanged.connect(self.refresh_log_display)
        self.filter_layout.addWidget(self.search_input)
        
        self.layout.addLayout(self.filter_layout)
        
        # Log terminal
        self.console = QTextBrowser()
        self.console.setStyleSheet("background-color: #08080a; border: 1px solid #2d2d34; border-radius: 8px;")
        self.layout.addWidget(self.console)
        
        # Clear & Export Action buttons
        self.btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear Output")
        self.btn_clear.clicked.connect(self.clear_logs)
        self.btn_layout.addWidget(self.btn_clear)
        
        self.btn_export = QPushButton("Export Log File")
        self.btn_export.clicked.connect(self.export_logs)
        self.btn_layout.addWidget(self.btn_export)
        
        self.layout.addLayout(self.btn_layout)
        
        # In-memory store
        self.log_history = [] # list of (level_name, formatted_msg)
        
        # Register python logging handler
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) %(message)s', '%H:%M:%S')
        self.handler = QLogHandler(self.log_received)
        self.handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.handler)
        
        # Add some initial log lines
        logging.getLogger("DASH").info("Diagnostic log manager initialized.")

    def log_received(self, levelname: str, message: str):
        self.log_history.append((levelname, message))
        # Cap log history at 2000 lines
        if len(self.log_history) > 2000:
            self.log_history.pop(0)
        self.append_log_line(levelname, message)

    def append_log_line(self, levelname: str, message: str):
        # Verify min level filter
        min_level_idx = self.combo_level.currentIndex()
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        
        try:
            curr_level_idx = levels.index(levelname)
        except ValueError:
            curr_level_idx = 1 # default info if weird
            
        if curr_level_idx < min_level_idx:
            return
            
        # Check text search filter
        search_txt = self.search_input.text().strip().lower()
        if search_txt and search_txt not in message.lower():
            return
            
        # Colors: Green for Info, Yellow for Warning, Red for Error, Gray for Debug
        colors = {
            "DEBUG": "#64748b",
            "INFO": "#00d2ff",
            "WARNING": "#ff9f1c",
            "ERROR": "#e63946"
        }
        color = colors.get(levelname, "#e2e8f0")
        
        # Append formatted line to terminal
        self.console.append(f"<font color='{color}'>{message}</font>")
        
        # Scroll
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def refresh_log_display(self):
        self.console.clear()
        for lvl, msg in self.log_history:
            self.append_log_line(lvl, msg)

    def clear_logs(self):
        self.log_history.clear()
        self.console.clear()

    def export_logs(self):
        if not self.log_history:
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export Log File", "dash_diagnostic_logs.txt", "Text Files (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for lvl, msg in self.log_history:
                        f.write(f"{msg}\n")
                QMessageBox.information(self, "Saved", f"Logs exported successfully to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log file: {e}")
