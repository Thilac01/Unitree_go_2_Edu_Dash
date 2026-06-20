from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QComboBox, QGroupBox, QProgressBar, QMessageBox
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from app.core.ssh_client import ssh_manager
from app.core.telemetry_bridge import telemetry_bridge
from app.core.network_troubleshooter import NetworkTroubleshooter
from app.core.database import db

class TabConnection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title
        self.layout.addWidget(QLabel("<h2>Robot Connection Wizard</h2>"))
        self.layout.addWidget(QLabel("<p style='color:#94a3b8;'>Select or create a connection profile to authenticate with the Unitree Go2 onboard computer.</p>"))
        
        # Profile selector and configuration fields
        self.config_group = QGroupBox("Configuration Profile")
        self.config_layout = QVBoxLayout(self.config_group)
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Profile:"))
        self.combo_profile = QComboBox()
        self.combo_profile.currentIndexChanged.connect(self.profile_changed)
        row1.addWidget(self.combo_profile)
        
        self.btn_delete_prof = QPushButton("Delete")
        self.btn_delete_prof.clicked.connect(self.delete_profile)
        row1.addWidget(self.btn_delete_prof)
        self.config_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Robot IP:"))
        self.ip_input = QLineEdit()
        row2.addWidget(self.ip_input)
        
        row2.addWidget(QLabel("SSH Port:"))
        self.port_input = QLineEdit("22")
        row2.addWidget(self.port_input)
        self.config_layout.addLayout(row2)
        
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Username:"))
        self.user_input = QLineEdit("unitree")
        row3.addWidget(self.user_input)
        
        row3.addWidget(QLabel("Password:"))
        self.pass_input = QLineEdit("123")
        self.pass_input.setEchoMode(QLineEdit.Password)
        row3.addWidget(self.pass_input)
        self.config_layout.addLayout(row3)
        
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("ROS Domain ID:"))
        self.domain_input = QLineEdit("0")
        row4.addWidget(self.domain_input)
        
        self.btn_save_prof = QPushButton("Save Profile As...")
        self.btn_save_prof.clicked.connect(self.save_profile)
        row4.addWidget(self.btn_save_prof)
        self.config_layout.addLayout(row4)
        
        self.layout.addWidget(self.config_group)
        
        # Wizard Steps display
        self.wizard_group = QGroupBox("Connection Sequence Status")
        self.wizard_layout = QVBoxLayout(self.wizard_group)
        
        self.steps_labels = []
        steps = [
            "1. Discover Robot on Subnet",
            "2. Ping Robot & Measure Latency",
            "3. Establish Secure SSH Connection",
            "4. Verify Onboard Unitree SDK Layer",
            "5. Verify ROS2 Environment",
            "6. Ready & Telemetry Synced"
        ]
        for step in steps:
            lbl = QLabel(f" ● {step}")
            lbl.setStyleSheet("color: #64748b; font-weight: 500;")
            self.steps_labels.append(lbl)
            self.wizard_layout.addWidget(lbl)
            
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 6)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00b4d8; }")
        self.wizard_layout.addWidget(self.progress_bar)
        
        self.layout.addWidget(self.wizard_group)
        
        # Connect & E-Stop
        self.btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("CONNECT TO ROBOT")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.clicked.connect(self.start_connection_wizard)
        self.btn_layout.addWidget(self.btn_connect)
        
        self.btn_disconnect = QPushButton("DISCONNECT")
        self.btn_disconnect.clicked.connect(self.disconnect_robot)
        self.btn_disconnect.setEnabled(False)
        self.btn_layout.addWidget(self.btn_disconnect)
        
        self.layout.addLayout(self.btn_layout)
        
        # Real-time state updates timer (for connection quality, battery)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_live_indicators)
        self.timer.start(1000)
        
        self.load_profiles()

    def load_profiles(self):
        self.combo_profile.clear()
        profiles = db.get_profiles()
        for p in profiles:
            self.combo_profile.addItem(p["profile_name"], p)
            if p["is_active"] == 1:
                idx = self.combo_profile.count() - 1
                self.combo_profile.setCurrentIndex(idx)
                
    def profile_changed(self, idx):
        if idx < 0:
            return
        p = self.combo_profile.itemData(idx)
        if p:
            self.ip_input.setText(p["ip_address"])
            self.port_input.setText(str(p["ssh_port"]))
            self.user_input.setText(p["username"])
            self.pass_input.setText(p["password"])
            self.domain_input.setText(str(p["ros_domain_id"]))
            db.set_active_profile(p["id"])

    def save_profile(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Profile", "Enter connection profile name:")
        if ok and name.strip():
            ip = self.ip_input.text()
            port = int(self.port_input.text())
            user = self.user_input.text()
            pswd = self.pass_input.text()
            domain = int(self.domain_input.text())
            
            if db.add_profile(name, ip, port, user, pswd, domain):
                self.load_profiles()
                QMessageBox.information(self, "Success", f"Profile '{name}' saved successfully.")

    def delete_profile(self):
        idx = self.combo_profile.currentIndex()
        if idx >= 0:
            p = self.combo_profile.itemData(idx)
            if p:
                if db.delete_profile(p["id"]):
                    self.load_profiles()
                    QMessageBox.information(self, "Deleted", "Profile removed.")

    def set_step_status(self, step_idx: int, status: str):
        """Sets step visual: status='active' (yellow), 'done' (cyan), 'fail' (red), 'idle' (gray)"""
        colors = {
            "idle": "color: #64748b;",
            "active": "color: #ff9f1c; font-weight: bold;",
            "done": "color: #00d2ff; font-weight: bold;",
            "fail": "color: #e63946; font-weight: bold;"
        }
        self.steps_labels[step_idx].setStyleSheet(colors[status])

    def reset_wizard_visuals(self):
        for i in range(6):
            self.set_step_status(i, "idle")
        self.progress_bar.setValue(0)

    def start_connection_wizard(self):
        self.reset_wizard_visuals()
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        
        # Fetch inputs
        ip = self.ip_input.text().strip()
        port_str = self.port_input.text().strip()
        user = self.user_input.text().strip()
        pswd = self.pass_input.text().strip()
        
        try:
            port = int(port_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", "Port must be an integer.")
            self.btn_connect.setEnabled(True)
            return
            
        # Run wizard asynchronously using timers to simulate steps without freezing UI
        self.current_wizard_ip = ip
        self.current_wizard_port = port
        self.current_wizard_user = user
        self.current_wizard_pass = pswd
        
        # Step 1: Discover
        self.set_step_status(0, "active")
        QTimer.singleShot(500, self.wizard_step1)

    def wizard_step1(self):
        subnet_check = NetworkTroubleshooter.check_subnet_match(self.current_wizard_ip)
        if subnet_check["match"] or self.current_wizard_ip == "127.0.0.1":
            self.set_step_status(0, "done")
            self.progress_bar.setValue(1)
            # Step 2: Ping
            self.set_step_status(1, "active")
            QTimer.singleShot(500, self.wizard_step2)
        else:
            self.set_step_status(0, "fail")
            QMessageBox.warning(self, "Subnet Mismatch", subnet_check["description"])
            self.abort_wizard()

    def wizard_step2(self):
        ping_check = NetworkTroubleshooter.ping_host(self.current_wizard_ip, count=2)
        if ping_check["success"] or self.current_wizard_ip == "127.0.0.1":
            self.set_step_status(1, "done")
            self.progress_bar.setValue(2)
            # Step 3: SSH Connect
            self.set_step_status(2, "active")
            QTimer.singleShot(500, self.wizard_step3)
        else:
            self.set_step_status(1, "fail")
            QMessageBox.warning(self, "Ping Failed", ping_check["description"])
            self.abort_wizard()

    def wizard_step3(self):
        # Trigger Paramiko client connect
        success = ssh_manager.connect(
            host=self.current_wizard_ip,
            port=self.current_wizard_port,
            username=self.current_wizard_user,
            password=self.current_wizard_pass
        )
        if success:
            self.set_step_status(2, "done")
            self.progress_bar.setValue(3)
            # Step 4: Verify SDK
            self.set_step_status(3, "active")
            QTimer.singleShot(500, self.wizard_step4)
        else:
            self.set_step_status(2, "fail")
            QMessageBox.warning(self, "SSH Authentication Failed", "Could not establish secure terminal connection. Verify password or network firewall port 22.")
            self.abort_wizard()

    def wizard_step4(self):
        # Verify python is available on the robot (standard check)
        status, out, err = ssh_manager.execute_command("python3 -V", timeout=3.0)
        python_ok = "Python" in out or self.current_wizard_ip == "127.0.0.1"
        
        if python_ok:
            self.set_step_status(3, "done")
        else:
            self.set_step_status(3, "fail")
            QMessageBox.warning(self, "Python Missing", "Could not locate python3 execution layer on remote robot.")
            self.abort_wizard()
            return

        self.progress_bar.setValue(4)
        # Always proceed to Step 5: Verify ROS
        self.set_step_status(4, "active")
        QTimer.singleShot(500, self.wizard_step5)

    def wizard_step5(self):
        # Check if ROS environment (like foxy or humble) directories exist or ros2 CLI is accessible
        status, out, err = ssh_manager.execute_command("ls /opt/ros/ || echo 'FAIL'", timeout=3.0)
        if ("foxy" in out or "humble" in out or "iron" in out) or self.current_wizard_ip == "127.0.0.1":
            self.set_step_status(4, "done")
            self.progress_bar.setValue(5)
            # Step 6: Ready & Telemetry Synced
            self.set_step_status(5, "active")
            QTimer.singleShot(500, self.wizard_step6)
        else:
            self.set_step_status(4, "fail")
            QMessageBox.warning(self, "ROS2 Missing", "Could not locate a standard ROS2 installation (foxy/humble/iron) under /opt/ros/ on the robot.")
            self.abort_wizard()

    def wizard_step6(self):
        # Auto-deploy telemetry bridge if not simulated
        if self.current_wizard_ip != "127.0.0.1":
            try:
                # 1. Upload dash_bridge.py
                import os
                # Find path to local dash_bridge.py
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                local_bridge = os.path.join(base_dir, "app", "robot_bridge", "dash_bridge.py")
                remote_bridge = "/home/unitree/dash_bridge.py"
                
                if os.path.exists(local_bridge) and ssh_manager.sftp:
                    ssh_manager.sftp.put(local_bridge, remote_bridge)
                    ssh_manager.execute_command(f"chmod +x {remote_bridge}")
                    
                    # 3. Kill any active daemon to prevent port bind conflicts
                    ssh_manager.execute_command("pkill -f dash_bridge.py")
                    
                    # 4. Start bridge in background, sourcing ROS2 beforehand
                    # All output is captured in /tmp/dash_bridge.log for debugging
                    log_file = "/tmp/dash_bridge.log"
                    launch_cmd = (
                        f"nohup bash -c '"
                        f"source /opt/ros/foxy/setup.bash 2>/dev/null || "
                        f"source /opt/ros/humble/setup.bash 2>/dev/null || "
                        f"source /opt/ros/iron/setup.bash 2>/dev/null; "
                        f"python3 {remote_bridge}' > {log_file} 2>&1 &"
                    )
                    _, out, err = ssh_manager.execute_command(launch_cmd, timeout=5.0)
                    if err and err.strip():
                        import logging as _log
                        _log.getLogger("DASH.ConnectionWizard").warning(
                            f"dash_bridge launch stderr: {err.strip()[:300]}"
                        )
                    logger.info(f"Telemetry bridge launched on robot. Logs at: {log_file}")
            except Exception as e:
                import logging
                logger = logging.getLogger("DASH.ConnectionWizard")
                logger.error(f"Failed to auto-deploy onboard telemetry bridge: {e}")

        # Start Telemetry Bridge on client side
        telemetry_bridge.set_connection(self.current_wizard_ip, 5555, simulated=(self.current_wizard_ip == "127.0.0.1"))
        telemetry_bridge.start()
        
        # Start SSH interactive shell terminal backing
        ssh_manager.start_interactive_shell()
        
        self.set_step_status(5, "done")
        self.progress_bar.setValue(6)
        
        # Enable actions in other panels
        self.btn_disconnect.setEnabled(True)
        self.btn_connect.setEnabled(False)

    def abort_wizard(self):
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    def disconnect_robot(self):
        telemetry_bridge.stop()
        ssh_manager.disconnect()
        self.reset_wizard_visuals()
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    def update_live_indicators(self):
        # We can update connection metrics
        pass
