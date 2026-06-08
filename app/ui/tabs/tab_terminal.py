from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel, QSplitter, QFileDialog, QMessageBox, QHeaderView
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSlot
from app.core.ssh_client import ssh_manager
from app.ui.widgets.terminal_widget import TerminalWidget
import os

class TabTerminal(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 1. Top One-Click SSH Buttons Bar
        self.action_layout = QHBoxLayout()
        
        self.btn_start_ros = QPushButton("Start ROS")
        self.btn_start_ros.clicked.connect(lambda: self.quick_exec("source /opt/ros/foxy/setup.bash && ros2 launch unitree_lidar_sdk launch.py"))
        self.action_layout.addWidget(self.btn_start_ros)
        
        self.btn_stop_ros = QPushButton("Stop ROS")
        self.btn_stop_ros.clicked.connect(lambda: self.quick_exec("pkill -f ros2"))
        self.action_layout.addWidget(self.btn_stop_ros)
        
        self.btn_start_slam = QPushButton("Start SLAM")
        self.btn_start_slam.clicked.connect(lambda: self.quick_exec("cd ~/SLAM && ./start_slam.sh"))
        self.action_layout.addWidget(self.btn_start_slam)
        
        self.btn_stop_slam = QPushButton("Stop SLAM")
        self.btn_stop_slam.clicked.connect(lambda: self.quick_exec("pkill -f slam"))
        self.action_layout.addWidget(self.btn_stop_slam)
        
        self.btn_reboot = QPushButton("Reboot Robot")
        self.btn_reboot.clicked.connect(lambda: self.quick_exec("sudo reboot"))
        self.btn_reboot.setStyleSheet("background-color: #ff9f1c; color: #121214;")
        self.action_layout.addWidget(self.btn_reboot)
        
        self.btn_shutdown = QPushButton("Shutdown")
        self.btn_shutdown.clicked.connect(lambda: self.quick_exec("sudo poweroff"))
        self.btn_shutdown.setStyleSheet("background-color: #e63946; color: white;")
        self.action_layout.addWidget(self.btn_shutdown)
        
        self.layout.addLayout(self.action_layout)
        
        # 2. Main Workspace Splitter (SFTP File Explorer on Left, Terminal on Right)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.layout.addWidget(self.splitter)
        
        # Left Panel - SFTP File Browser
        self.sftp_widget = QWidget()
        self.sftp_layout = QVBoxLayout(self.sftp_widget)
        self.sftp_layout.setContentsMargins(0, 0, 5, 0)
        
        # Path Bar
        path_layout = QHBoxLayout()
        self.lbl_path = QLabel("Remote Path:")
        path_layout.addWidget(self.lbl_path)
        self.path_input = QLineEdit("/home/unitree")
        self.path_input.returnPressed.connect(self.load_remote_dir)
        path_layout.addWidget(self.path_input)
        
        self.btn_up_dir = QPushButton("↑")
        self.btn_up_dir.setFixedWidth(30)
        self.btn_up_dir.clicked.connect(self.navigate_up)
        path_layout.addWidget(self.btn_up_dir)
        
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_remote_dir)
        path_layout.addWidget(self.btn_refresh)
        self.sftp_layout.addLayout(path_layout)
        
        # File Table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["Name", "Type", "Size (Bytes)"])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.doubleClicked.connect(self.file_double_clicked)
        self.sftp_layout.addWidget(self.file_table)
        
        # Upload / Download buttons
        sftp_btn_layout = QHBoxLayout()
        self.btn_upload = QPushButton("Upload File")
        self.btn_upload.clicked.connect(self.upload_file)
        sftp_btn_layout.addWidget(self.btn_upload)
        
        self.btn_download = QPushButton("Download Selected")
        self.btn_download.clicked.connect(self.download_file)
        sftp_btn_layout.addWidget(self.btn_download)
        self.sftp_layout.addLayout(sftp_btn_layout)
        
        self.splitter.addWidget(self.sftp_widget)
        
        # Right Panel - Monospace Interactive Terminal
        self.terminal = TerminalWidget()
        self.splitter.addWidget(self.terminal)
        
        self.splitter.setSizes([350, 650])
        
        # Keep track of path
        self.current_remote_path = "/home/unitree"
        
        # Register SSH status connection listeners to trigger refresh
        ssh_manager.connection_status.connect(self.on_ssh_status_changed)

    def on_ssh_status_changed(self, connected: bool, msg: str):
        if connected:
            self.load_remote_dir()
        else:
            self.file_table.setRowCount(0)

    def quick_exec(self, cmd: str):
        if not ssh_manager.is_connected():
            QMessageBox.warning(self, "Offline", "SSH not connected to robot.")
            return
        ssh_manager.write_to_shell(cmd + "\n")

    def load_remote_dir(self):
        if not ssh_manager.is_connected():
            return
            
        path = self.path_input.text().strip()
        entries = ssh_manager.list_remote_dir(path)
        
        # Keep internal record
        self.current_remote_path = path
        
        self.file_table.setRowCount(len(entries))
        for idx, entry in enumerate(entries):
            # 1. Name
            item_name = QTableWidgetItem(entry["name"])
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.file_table.setItem(idx, 0, item_name)
            
            # 2. Type
            ftype = "Folder" if entry["is_dir"] else "File"
            item_type = QTableWidgetItem(ftype)
            item_type.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if entry["is_dir"]:
                item_type.setForeground(QColor("#00d2ff")) # Color folder item cyan
            self.file_table.setItem(idx, 1, item_type)
            
            # 3. Size
            sz_str = str(entry["size"]) if not entry["is_dir"] else "-"
            item_size = QTableWidgetItem(sz_str)
            item_size.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.file_table.setItem(idx, 2, item_size)

    def file_double_clicked(self, index):
        row = index.row()
        name_item = self.file_table.item(row, 0)
        type_item = self.file_table.item(row, 1)
        
        if name_item and type_item:
            name = name_item.text()
            if type_item.text() == "Folder":
                # Navigate inside
                new_path = os.path.posixpath.join(self.current_remote_path, name)
                self.path_input.setText(new_path)
                self.load_remote_dir()

    def navigate_up(self):
        parts = self.current_remote_path.rstrip('/').split('/')
        if len(parts) > 1:
            new_path = "/".join(parts[:-1])
            if not new_path:
                new_path = "/"
            self.path_input.setText(new_path)
            self.load_remote_dir()

    def upload_file(self):
        if not ssh_manager.is_connected():
            return
            
        local_file, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
        if local_file:
            filename = os.path.basename(local_file)
            remote_dest = os.path.posixpath.join(self.current_remote_path, filename)
            ssh_manager.upload_file(local_file, remote_dest)
            QMessageBox.information(self, "Upload Started", f"Uploading {filename} to {self.current_remote_path}...")
            # Auto refresh in 2 seconds
            import PyQt5.QtCore as QtCore
            QtCore.QTimer.singleShot(2000, self.load_remote_dir)

    def download_file(self):
        if not ssh_manager.is_connected():
            return
            
        selected_ranges = self.file_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "No Selection", "Please select a file in the table to download.")
            return
            
        row = selected_ranges[0].topRow()
        name = self.file_table.item(row, 0).text()
        ftype = self.file_table.item(row, 1).text()
        
        if ftype == "Folder":
            QMessageBox.warning(self, "Invalid Selection", "Downloading entire folders via SFTP is not supported. Please select individual files.")
            return
            
        local_dest, _ = QFileDialog.getSaveFileName(self, "Save Downloaded File", name)
        if local_dest:
            remote_source = os.path.posixpath.join(self.current_remote_path, name)
            ssh_manager.download_file(remote_source, local_dest)
            QMessageBox.information(self, "Download Started", f"Downloading {name} to local system...")
