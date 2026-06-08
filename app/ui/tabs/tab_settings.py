import os
import platform
import shutil
import subprocess
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QCheckBox, QGroupBox, QGridLayout, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt, pyqtSlot
from app.core.database import db

class TabSettings(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title
        self.layout.addWidget(QLabel("<h2>Application Settings & Profiles</h2>"))
        
        # Splitter Layout
        self.main_layout = QHBoxLayout()
        self.layout.addLayout(self.main_layout)
        
        # Left Panel - ROS Environment Manager
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 5, 0)
        
        self.ros_group = QGroupBox("ROS Environment Manager (on Robot/WSL)")
        self.ros_layout = QVBoxLayout(self.ros_group)
        
        self.lbl_ros_detected = QLabel("Probing WSL for local ROS distributions...")
        self.lbl_ros_detected.setStyleSheet("color: #ff9f1c;")
        self.ros_layout.addWidget(self.lbl_ros_detected)
        
        # Activation Buttons
        self.btn_foxy = QPushButton("Activate ROS Foxy")
        self.btn_foxy.clicked.connect(lambda: self.activate_ros("foxy"))
        self.ros_layout.addWidget(self.btn_foxy)
        
        self.btn_humble = QPushButton("Activate ROS Humble")
        self.btn_humble.clicked.connect(lambda: self.activate_ros("humble"))
        self.ros_layout.addWidget(self.btn_humble)
        
        self.btn_iron = QPushButton("Activate ROS Iron")
        self.btn_iron.clicked.connect(lambda: self.activate_ros("iron"))
        self.ros_layout.addWidget(self.btn_iron)
        
        self.lbl_active_ros = QLabel("Active Environment: None Sourced")
        self.lbl_active_ros.setStyleSheet("font-family: Consolas; font-weight: bold; color: #00d2ff;")
        self.ros_layout.addWidget(self.lbl_active_ros)
        
        self.left_layout.addWidget(self.ros_group)
        self.main_layout.addWidget(self.left_panel, 1)
        
        # Right Panel - Theme and Backups
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(5, 0, 0, 0)
        
        # Theme / General settings
        self.gen_group = QGroupBox("Application General Configurations")
        self.gen_layout = QVBoxLayout(self.gen_group)
        
        self.chk_dark = QCheckBox("Enforce Ground Control Dark Theme")
        self.chk_dark.setChecked(True)
        self.gen_layout.addWidget(self.chk_dark)
        
        self.chk_updates = QCheckBox("Enable Automatic Firmware Checker")
        self.chk_updates.setChecked(False)
        self.gen_layout.addWidget(self.chk_updates)
        
        self.right_layout.addWidget(self.gen_group)
        
        # Backup / Restore
        self.db_group = QGroupBox("Configuration Databases Management")
        self.db_layout = QVBoxLayout(self.db_group)
        
        self.btn_backup = QPushButton("Backup Settings Database")
        self.btn_backup.clicked.connect(self.backup_db)
        self.db_layout.addWidget(self.btn_backup)
        
        self.btn_restore = QPushButton("Restore Settings Database")
        self.btn_restore.clicked.connect(self.restore_db)
        self.db_layout.addWidget(self.btn_restore)
        
        self.right_layout.addWidget(self.db_group)
        self.right_layout.addStretch()
        self.main_layout.addWidget(self.right_panel, 1)
        
        # Run detection and refresh label
        self.detect_ros_environments()
        self.refresh_active_ros_label()

    def detect_ros_environments(self):
        """Probes WSL/Ubuntu to detect installed ROS distros."""
        wsl = shutil.which("wsl")
        if not wsl:
            self.lbl_ros_detected.setText("No local WSL environment found. Telemetry operates over SSH connections.")
            self.lbl_ros_detected.setStyleSheet("color: #64748b;")
            return
            
        try:
            # Run query in Ubuntu inside WSL
            cmd = ["wsl", "ls", "/opt/ros/"]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode('utf-8', errors='ignore')
            
            detected = []
            if "foxy" in output:
                detected.append("Foxy")
            if "humble" in output:
                detected.append("Humble")
            if "iron" in output:
                detected.append("Iron")
                
            if detected:
                self.lbl_ros_detected.setText(f"WSL Detected ROS Distros: {', '.join(detected)}")
                self.lbl_ros_detected.setStyleSheet("color: #00d2ff;")
            else:
                self.lbl_ros_detected.setText("WSL detected but /opt/ros/ is empty. Please install ROS in Ubuntu.")
                self.lbl_ros_detected.setStyleSheet("color: #ff9f1c;")
        except Exception:
            self.lbl_ros_detected.setText("WSL is installed but querying /opt/ros/ directories timed out.")
            self.lbl_ros_detected.setStyleSheet("color: #e63946;")

    def refresh_active_ros_label(self):
        active_distro = db.get_setting("active_ros_distro", "None Sourced (Direct Mode)")
        self.lbl_active_ros.setText(f"Active Environment: {active_distro.upper()}")

    def activate_ros(self, distro: str):
        # Save active distro inside settings database
        db.set_setting("active_ros_distro", distro)
        self.refresh_active_ros_label()
        
        # Store source command wrapper prefix in DB settings
        prefix_command = f"source /opt/ros/{distro}/setup.bash"
        db.set_setting("ros_source_command", prefix_command)
        
        QMessageBox.information(
            self, 
            "ROS Activated", 
            f"ROS {distro.capitalize()} activated successfully.\nAll remote commands will now automatically compile after sourcing {distro} paths."
        )

    def backup_db(self):
        path, _ = QFileDialog.getSaveFileName(self, "Backup Database", "dash_settings_backup.db", "SQLite DB (*.db)")
        if path:
            try:
                import shutil
                shutil.copy(db.db_path, path)
                QMessageBox.information(self, "Success", f"Settings database backed up to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Failed to back up: {e}")

    def restore_db(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore Database", "", "SQLite DB (*.db)")
        if path:
            try:
                import shutil
                shutil.copy(path, db.db_path)
                QMessageBox.information(self, "Success", "Database successfully restored. Please restart DASH to reload configurations.")
            except Exception as e:
                QMessageBox.critical(self, "Restore Failed", f"Failed to restore settings: {e}")
