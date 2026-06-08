from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QListWidget, QSplitter
from PyQt5.QtGui import QFont, QKeyEvent
from PyQt5.QtCore import Qt, pyqtSlot
from app.core.ssh_client import ssh_manager
from app.core.database import db

class TerminalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter to separate quick commands and console
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.layout.addWidget(self.splitter)
        
        # Left Panel - Saved Commands
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(5, 5, 5, 5)
        
        self.left_layout.addWidget(QLabel("<b>Saved Shortcuts</b>"))
        self.saved_list = QListWidget()
        self.saved_list.itemDoubleClicked.connect(self.run_saved_item)
        self.left_layout.addWidget(self.saved_list)
        
        # Short-cut additions
        self.cmd_name_input = QLineEdit()
        self.cmd_name_input.setPlaceholderText("Shortcut Name")
        self.cmd_str_input = QLineEdit()
        self.cmd_str_input.setPlaceholderText("bash command...")
        
        self.btn_add_cmd = QPushButton("Add Shortcut")
        self.btn_add_cmd.clicked.connect(self.add_shortcut)
        self.left_layout.addWidget(self.cmd_name_input)
        self.left_layout.addWidget(self.cmd_str_input)
        self.left_layout.addWidget(self.btn_add_cmd)
        
        self.splitter.addWidget(self.left_panel)
        
        # Right Panel - Terminal Console
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Monospace Shell Text Box
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        font = QFont("Consolas", 11)
        self.console.setFont(font)
        self.console.setStyleSheet("background-color: #0b0b0d; color: #00ff66; border: 1px solid #2d2d34;")
        self.right_layout.addWidget(self.console)
        
        # Command input
        self.input_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setFont(font)
        self.cmd_input.setPlaceholderText("Type command here and press Enter...")
        self.cmd_input.returnPressed.connect(self.send_command)
        self.input_layout.addWidget(self.cmd_input)
        
        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self.send_command)
        self.input_layout.addWidget(self.btn_send)
        self.right_layout.addLayout(self.input_layout)
        
        self.splitter.addWidget(self.right_panel)
        
        # Configure Splitter sizes (1:4 ratio)
        self.splitter.setSizes([200, 800])
        
        # Connect to SSH signals
        ssh_manager.shell_data_received.connect(self.append_output)
        
        self.refresh_shortcuts()

    def refresh_shortcuts(self):
        self.saved_list.clear()
        cmds = db.get_saved_commands()
        for cmd in cmds:
            item_text = f"{cmd['name']} - {cmd['description']}"
            self.saved_list.addItem(item_text)
            # Store ID in user data role
            self.saved_list.item(self.saved_list.count()-1).setData(Qt.UserRole, cmd)

    def run_saved_item(self, item):
        cmd_data = item.data(Qt.UserRole)
        if cmd_data:
            cmd = cmd_data["command"]
            self.console.append(f"\n> Running shortcut: {cmd}\n")
            ssh_manager.write_to_shell(cmd + "\n")

    def add_shortcut(self):
        name = self.cmd_name_input.text().strip()
        cmd = self.cmd_str_input.text().strip()
        if name and cmd:
            if db.add_saved_command(name, cmd, "User added shortcut"):
                self.refresh_shortcuts()
                self.cmd_name_input.clear()
                self.cmd_str_input.clear()

    @pyqtSlot(str)
    def append_output(self, text: str):
        # Clean terminal backspaces and carriage returns
        text_clean = text.replace('\r\n', '\n').replace('\r', '')
        # Move cursor to end and insert
        cursor = self.console.textCursor()
        cursor.movePosition(cursor.End)
        self.console.setTextCursor(cursor)
        self.console.insertPlainText(text_clean)
        # Scroll down
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def send_command(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
            
        if not ssh_manager.is_connected():
            self.console.append("\n[ERROR] SSH is not connected to the robot.\n")
            return
            
        db.add_command_history(cmd)
        
        # Send to paramiko shell
        ssh_manager.write_to_shell(cmd + "\n")
        self.cmd_input.clear()

    # Capture direct keystrokes if focused to allow interactiveness (e.g. CTRL+C)
    def keyPressEvent(self, event: QKeyEvent):
        if self.cmd_input.hasFocus():
            # Let standard line-edit handle it
            super().keyPressEvent(event)
            return
            
        # Send raw control keys (e.g., CTRL+C) directly to remote shell
        if event.modifiers() & Qt.ControlModifier:
            key = event.key()
            if key == Qt.Key_C:
                ssh_manager.write_to_shell("\x03") # SIGINT
                event.accept()
                return
            elif key == Qt.Key_Z:
                ssh_manager.write_to_shell("\x1a") # SIGTSTP
                event.accept()
                return
                
        super().keyPressEvent(event)
