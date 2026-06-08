from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QPushButton, QProgressBar, QTextBrowser
from PyQt5.QtCore import pyqtSlot, Qt
from app.core.telemetry_bridge import telemetry_bridge
from app.core.ssh_client import ssh_manager
from app.ui.widgets.sensor_card import SensorCard

class TabDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(15)
        
        # 1. Welcome Header
        self.header_layout = QHBoxLayout()
        self.lbl_title = QLabel("<h1>GROUND CONTROL DASHBOARD</h1>")
        self.lbl_title.setStyleSheet("margin: 0px; padding: 0px;")
        self.header_layout.addWidget(self.lbl_title)
        
        self.lbl_status = QLabel("SYSTEM: NOMINAL")
        self.lbl_status.setStyleSheet("background-color: #00d2ff; color: #121214; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")
        self.header_layout.addWidget(self.lbl_status)
        self.header_layout.addStretch()
        self.layout.addLayout(self.header_layout)
        
        # 2. Top Metric Cards Row
        self.cards_layout = QHBoxLayout()
        self.card_bat = SensorCard("Power Source", "%")
        self.card_temp = SensorCard("Board Temperature", "°C")
        self.card_signal = SensorCard("Link Quality", "%")
        self.card_ros = SensorCard("Active Middleware", "")
        
        self.cards_layout.addWidget(self.card_bat)
        self.cards_layout.addWidget(self.card_temp)
        self.cards_layout.addWidget(self.card_signal)
        self.cards_layout.addWidget(self.card_ros)
        self.layout.addLayout(self.cards_layout)
        
        # 3. Main Center Workspace (Quick Commands & Hardware Health Split)
        self.center_layout = QHBoxLayout()
        self.layout.addLayout(self.center_layout)
        
        # Left Panel - Robot Quick Actions
        self.quick_group = QGroupBox("Fast Commands Desk")
        self.quick_layout = QGridLayout(self.quick_group)
        self.quick_layout.setContentsMargins(15, 20, 15, 15)
        self.quick_layout.setSpacing(10)
        
        self.btn_stand = QPushButton("Stand Up")
        self.btn_stand.setMinimumHeight(45)
        self.btn_stand.clicked.connect(lambda: self.exec_remote_cmd("stand"))
        self.quick_layout.addWidget(self.btn_stand, 0, 0)
        
        self.btn_sit = QPushButton("Sit Down")
        self.btn_sit.setMinimumHeight(45)
        self.btn_sit.clicked.connect(lambda: self.exec_remote_cmd("sit"))
        self.quick_layout.addWidget(self.btn_sit, 0, 1)
        
        self.btn_dance = QPushButton("Performance Dance")
        self.btn_dance.setMinimumHeight(45)
        self.btn_dance.clicked.connect(lambda: self.exec_remote_cmd("dance"))
        self.quick_layout.addWidget(self.btn_dance, 1, 0)
        
        self.btn_recovery = QPushButton("Recovery Pose")
        self.btn_recovery.setMinimumHeight(45)
        self.btn_recovery.clicked.connect(lambda: self.exec_remote_cmd("recovery_stand"))
        self.quick_layout.addWidget(self.btn_recovery, 1, 1)
        
        self.btn_start_slam = QPushButton("Launch SLAM Node")
        self.btn_start_slam.setObjectName("btn_start_slam") # Orange/cyan highlight
        self.btn_start_slam.setMinimumHeight(45)
        self.quick_layout.addWidget(self.btn_start_slam, 2, 0, 1, 2)
        
        self.center_layout.addWidget(self.quick_group, 2)
        
        # Right Panel - Onboard CPU / Resource Logs
        self.stats_group = QGroupBox("Host & Onboard Resource Load")
        self.stats_layout = QVBoxLayout(self.stats_group)
        self.stats_layout.setContentsMargins(15, 20, 15, 15)
        
        self.stats_layout.addWidget(QLabel("Onboard CPU Load:"))
        self.progress_cpu = QProgressBar()
        self.progress_cpu.setRange(0, 100)
        self.progress_cpu.setValue(0)
        self.progress_cpu.setStyleSheet("QProgressBar { border: 1px solid #2d2d34; border-radius: 4px; background: #121214; text-align: center; } QProgressBar::chunk { background: #00b4d8; }")
        self.stats_layout.addWidget(self.progress_cpu)
        
        self.stats_layout.addWidget(QLabel("Onboard Memory Usage:"))
        self.progress_ram = QProgressBar()
        self.progress_ram.setRange(0, 100)
        self.progress_ram.setValue(0)
        self.progress_ram.setStyleSheet("QProgressBar { border: 1px solid #2d2d34; border-radius: 4px; background: #121214; text-align: center; } QProgressBar::chunk { background: #00ffcc; }")
        self.stats_layout.addWidget(self.progress_ram)
        
        self.stats_layout.addWidget(QLabel("System Diagnostics Messages:"))
        self.diagnostics_box = QTextBrowser()
        self.diagnostics_box.setStyleSheet("background-color: #08080a; border: 1px solid #2d2d34; border-radius: 6px;")
        self.diagnostics_box.append("[INFO] Dashboard aggregator node connected.")
        self.stats_layout.addWidget(self.diagnostics_box)
        
        self.center_layout.addWidget(self.stats_group, 3)
        
        # Bind telemetry
        telemetry_bridge.telemetry_received.connect(self.on_telemetry)

    @pyqtSlot(dict)
    def on_telemetry(self, data: dict):
        # Update Cards
        bat = data.get("battery", {})
        bat_pct = bat.get("percentage", 100)
        self.card_bat.update_value(bat_pct, status="ok" if bat_pct > 20 else "error", status_text=f"Voltage: {bat.get('voltage', 24.0):.1f}V")
        
        sys = data.get("system", {})
        temp = sys.get("temperature", 45.0)
        self.card_temp.update_value(temp, status="ok" if temp < 65.0 else "warning", status_text=f"SBC Core Temp")
        
        net = sys.get("network_quality", 100)
        self.card_signal.update_value(net, status="ok" if net > 75 else "warning", status_text="Wi-Fi Signal Strength" if not telemetry_bridge.simulated else "Simulated Link")
        
        ros_str = sys.get("ros_state", "Offline")
        self.card_ros.update_value("ROS2 Foxy" if "Foxy" in ros_str else ("ROS2 Humble" if "Humble" in ros_str else "Direct ZMQ"), status="ok", status_text="Middleware Active")
        
        # Update progress loads
        self.progress_cpu.setValue(int(sys.get("cpu", 0.0)))
        self.progress_ram.setValue(int(sys.get("ram", 0.0)))
        
        # System health status bar mapping
        if temp > 70.0 or bat_pct < 15:
            self.lbl_status.setText("SYSTEM: WARNING")
            self.lbl_status.setStyleSheet("background-color: #ff9f1c; color: #121214; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")
        elif not ssh_manager.is_connected() and not telemetry_bridge.simulated:
            self.lbl_status.setText("SYSTEM: DISCONNECTED")
            self.lbl_status.setStyleSheet("background-color: #e63946; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")
        else:
            self.lbl_status.setText("SYSTEM: NOMINAL")
            self.lbl_status.setStyleSheet("background-color: #00d2ff; color: #121214; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")

    def exec_remote_cmd(self, action: str):
        if not ssh_manager.is_connected():
            self.diagnostics_box.append(f"<font color='#ff9f1c'>[WARN] Connect to robot via SSH before triggering '{action}'.</font>")
            return
            
        self.diagnostics_box.append(f"[CMD] Transmitting posture payload: {action}")
        ssh_manager.write_to_shell(f"python3 ~/actions/{action}.py || echo 'Action sent'\n")
