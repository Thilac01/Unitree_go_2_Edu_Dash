from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QGridLayout, QTextBrowser, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSlot
from app.core.ssh_client import ssh_manager
from app.core.telemetry_bridge import telemetry_bridge

class TabSLAM(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title
        self.layout.addWidget(QLabel("<h2>SLAM Control & Mapping Center</h2>"))
        self.layout.addWidget(QLabel("<p style='color:#94a3b8;'>Orchestrate onboard Lidar SLAM mapping nodes. Replace manual terminal commands with graphical triggers.</p>"))
        
        # Splitter or Horizontal Layout
        self.main_layout = QHBoxLayout()
        self.layout.addLayout(self.main_layout)
        
        # Left Panel - Buttons and Status cards
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        # SLAM Actions
        self.action_group = QGroupBox("SLAM Commands")
        self.action_grid = QGridLayout(self.action_group)
        
        self.btn_start = QPushButton("Start SLAM")
        self.btn_start.setObjectName("btn_start_slam") # Neon Accent
        self.btn_start.clicked.connect(self.start_slam)
        self.action_grid.addWidget(self.btn_start, 0, 0)
        
        self.btn_pause = QPushButton("Pause SLAM")
        self.btn_pause.clicked.connect(self.pause_slam)
        self.action_grid.addWidget(self.btn_pause, 0, 1)
        
        self.btn_stop = QPushButton("Stop SLAM")
        self.btn_stop.clicked.connect(self.stop_slam)
        self.btn_stop.setStyleSheet("background-color:#e63946; color:white;")
        self.action_grid.addWidget(self.btn_stop, 1, 0)
        
        self.btn_clear = QPushButton("Clear Map")
        self.btn_clear.clicked.connect(self.clear_map)
        self.action_grid.addWidget(self.btn_clear, 1, 1)
        
        self.btn_save_map = QPushButton("Save Map")
        self.btn_save_map.clicked.connect(self.save_map)
        self.action_grid.addWidget(self.btn_save_map, 2, 0)
        
        self.btn_load_map = QPushButton("Load Map")
        self.btn_load_map.clicked.connect(self.load_map)
        self.action_grid.addWidget(self.btn_load_map, 2, 1)
        
        self.btn_mapping_mode = QPushButton("Mapping Mode")
        self.btn_mapping_mode.clicked.connect(lambda: self.set_mode("mapping"))
        self.action_grid.addWidget(self.btn_mapping_mode, 3, 0)
        
        self.btn_loc_mode = QPushButton("Localization Mode")
        self.btn_loc_mode.clicked.connect(lambda: self.set_mode("localization"))
        self.action_grid.addWidget(self.btn_loc_mode, 3, 1)
        
        self.left_layout.addWidget(self.action_group)
        
        # SLAM Telemetry Monitor Card
        self.telemetry_group = QGroupBox("Mapping Indicators")
        self.telemetry_grid = QGridLayout(self.telemetry_group)
        
        self.lbl_status = QLabel("SLAM STATUS: IDLE")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff9f1c;")
        self.telemetry_grid.addWidget(self.lbl_status, 0, 0, 1, 2)
        
        self.lbl_closures = QLabel("Loop Closures: 0")
        self.telemetry_grid.addWidget(self.lbl_closures, 1, 0)
        
        self.lbl_points = QLabel("Point Count: 0")
        self.telemetry_grid.addWidget(self.lbl_points, 1, 1)
        
        self.lbl_confidence = QLabel("Localization Confidence: 0.0%")
        self.telemetry_grid.addWidget(self.lbl_confidence, 2, 0)
        
        self.lbl_runtime = QLabel("Runtime: 0.0s")
        self.telemetry_grid.addWidget(self.lbl_runtime, 2, 1)
        
        self.left_layout.addWidget(self.telemetry_group)
        self.main_layout.addWidget(self.left_panel)
        
        # Right Panel - SLAM Monospace Terminal Feedback
        self.log_group = QGroupBox("SLAM Process Terminal Output")
        self.log_layout = QVBoxLayout(self.log_group)
        self.log_console = QTextBrowser()
        self.log_console.append("SLAM engine is currently offline. Press 'Start SLAM' to launch remote nodes.")
        self.log_layout.addWidget(self.log_console)
        self.main_layout.addWidget(self.log_group)
        
        # Subscriptions
        telemetry_bridge.telemetry_received.connect(self.on_telemetry)

    @pyqtSlot(dict)
    def on_telemetry(self, data: dict):
        slam = data.get("slam", {})
        status = slam.get("status", "Idle")
        
        self.lbl_status.setText(f"SLAM STATUS: {status.upper()}")
        if status.lower() in ["mapping", "localizing", "running"]:
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #00d2ff;")
        else:
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #64748b;")
            
        self.lbl_closures.setText(f"Loop Closures: {slam.get('loop_closures', 0)}")
        self.lbl_points.setText(f"Point Count: {slam.get('point_count', 0)}")
        self.lbl_confidence.setText(f"Localization Confidence: {slam.get('confidence', 0.0):.1f}%")
        self.lbl_runtime.setText(f"Runtime: {slam.get('runtime', 0.0):.1f}s")

    def start_slam(self):
        if not ssh_manager.is_connected():
            QMessageBox.warning(self, "Offline", "Must connect to robot before launching SLAM.")
            return
            
        self.log_console.append("\n> Sourcing environment and launching SLAM stack...")
        cmd = "cd ~/SLAM && ./start_slam.sh"
        ssh_manager.write_to_shell(cmd + "\n")
        self.log_console.append("[INFO] Launched. Subscribing to point cloud and tf topics.")

    def pause_slam(self):
        if ssh_manager.is_connected():
            self.log_console.append("\n> Pausing SLAM nodes...")
            ssh_manager.write_to_shell("ros2 service call /pause_slam std_srvs/srv/Empty {}\n")

    def stop_slam(self):
        if ssh_manager.is_connected():
            self.log_console.append("\n> Stopping SLAM nodes...")
            ssh_manager.write_to_shell("pkill -f slam\n")
            self.log_console.append("[INFO] SLAM processes killed.")

    def clear_map(self):
        if ssh_manager.is_connected():
            self.log_console.append("\n> Clearing active map database...")
            ssh_manager.write_to_shell("ros2 service call /clear_map std_srvs/srv/Empty {}\n")

    def save_map(self):
        if ssh_manager.is_connected():
            self.log_console.append("\n> Saving active octomap/gridmap to remote disk...")
            ssh_manager.write_to_shell("ros2 service call /save_map std_srvs/srv/Empty {}\n")
            QMessageBox.information(self, "Map Saved", "Map successfully saved on robot SBC storage (~/maps/saved_map).")

    def load_map(self):
        if ssh_manager.is_connected():
            self.log_console.append("\n> Loading map from default directory...")
            ssh_manager.write_to_shell("ros2 launch SLAM load_map.launch.py\n")

    def set_mode(self, mode: str):
        if ssh_manager.is_connected():
            self.log_console.append(f"\n> Switching to SLAM {mode} mode...")
            ssh_manager.write_to_shell(f"ros2 param set /slam_node mode {mode}\n")
