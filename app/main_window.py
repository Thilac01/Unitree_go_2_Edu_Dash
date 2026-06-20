import time
from PyQt5.QtWidgets import QMainWindow, QWidget, QSplitter, QListWidget, QStackedWidget, QToolBar, QPushButton, QLabel, QProgressBar, QHBoxLayout, QStatusBar, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QFont

# Core Subsystems
from app.core.ssh_client import ssh_manager
from app.core.telemetry_bridge import telemetry_bridge
from app.core.database import db

# Tab Pages
from app.ui.tabs.tab_preflight import TabPreflight
from app.ui.tabs.tab_connection import TabConnection
from app.ui.tabs.tab_terminal import TabTerminal
from app.ui.tabs.tab_slam import TabSLAM
from app.ui.tabs.tab_pointcloud import TabPointCloud
from app.ui.tabs.tab_camera import TabCamera
from app.ui.tabs.tab_sensors import TabSensors
from app.ui.tabs.tab_motor import TabMotor
from app.ui.tabs.tab_control import TabControl
from app.ui.tabs.tab_explorer import TabExplorer
from app.ui.tabs.tab_api import TabAPI
from app.ui.tabs.tab_websocket import TabWebSocket
from app.ui.tabs.tab_logging import TabLogging
from app.ui.tabs.tab_settings import TabSettings
from app.ui.tabs.tab_dashboard import TabDashboard

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DASH // Unitree Go2 EDU Ground Station")
        self.resize(1366, 768)
        
        # 1. Top Toolbar Setup
        self.toolbar = QToolBar("Diagnostics Bar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        self.setup_toolbar()
        
        # 2. Main Window Layout Manager (Splitter)
        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)
        
        # Left Sidebar Navigation
        self.sidebar = QListWidget()
        self.setup_sidebar()
        self.splitter.addWidget(self.sidebar)
        
        # Center Stacked Workspace
        self.workspace = QStackedWidget()
        self.setup_workspace()
        self.splitter.addWidget(self.workspace)
        
        # Splitter sizing (1:5 ratio)
        self.splitter.setSizes([220, 1146])
        
        # 3. Bottom Status Bar Setup
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.setup_statusbar()
        
        # Telemetry Connection
        telemetry_bridge.telemetry_received.connect(self.on_telemetry_tick)
        ssh_manager.connection_status.connect(self.on_ssh_status)
        
        # Connect Custom Signals & Buttons
        self.tab_preflight.checklist_resolved.connect(self.on_checklist_resolved)
        self.tab_dashboard.btn_start_slam.clicked.connect(self.launch_slam_from_dashboard)
        
        # Fast timer to measure latency & update connection stats
        self.ping_timer = QTimer()
        self.ping_timer.timeout.connect(self.measure_connection_health)
        self.ping_timer.start(2000)
        
    def setup_toolbar(self):
        # Connection Status
        self.lbl_conn = QLabel("OFFLINE")
        self.lbl_conn.setStyleSheet("background-color: #e63946; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        self.toolbar.addWidget(self.lbl_conn)
        
        self.toolbar.addSeparator()
        
        # Battery
        self.toolbar.addWidget(QLabel("BAT:"))
        self.bar_battery = QProgressBar()
        self.bar_battery.setFixedSize(80, 14)
        self.bar_battery.setRange(0, 100)
        self.bar_battery.setValue(100)
        self.bar_battery.setTextVisible(True)
        self.bar_battery.setStyleSheet("QProgressBar { border: 1px solid #2d2d34; border-radius: 3px; background: #121214; text-align: center; font-size: 9px; } QProgressBar::chunk { background: #00b4d8; }")
        self.toolbar.addWidget(self.bar_battery)
        
        self.toolbar.addSeparator()
        
        # State indicators
        self.lbl_state = QLabel("STATE: STANDBY")
        self.lbl_state.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.toolbar.addWidget(self.lbl_state)
        
        # SLAM state
        self.lbl_slam_state = QLabel("SLAM: IDLE")
        self.lbl_slam_state.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.toolbar.addWidget(self.lbl_slam_state)
        
        # ROS state
        self.lbl_ros_state = QLabel("ROS: OFFLINE")
        self.lbl_ros_state.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.toolbar.addWidget(self.lbl_ros_state)
        
        self.toolbar.addSeparator()
        
        # CPU Usage
        self.toolbar.addWidget(QLabel("CPU:"))
        self.bar_cpu = QProgressBar()
        self.bar_cpu.setFixedSize(70, 14)
        self.bar_cpu.setValue(0)
        self.bar_cpu.setStyleSheet("QProgressBar { border: 1px solid #2d2d34; border-radius: 3px; background: #121214; } QProgressBar::chunk { background: #00ffcc; }")
        self.toolbar.addWidget(self.bar_cpu)
        
        # RAM Usage
        self.toolbar.addWidget(QLabel("RAM:"))
        self.bar_ram = QProgressBar()
        self.bar_ram.setFixedSize(70, 14)
        self.bar_ram.setValue(0)
        self.bar_ram.setStyleSheet("QProgressBar { border: 1px solid #2d2d34; border-radius: 3px; background: #121214; } QProgressBar::chunk { background: #00ffcc; }")
        self.toolbar.addWidget(self.bar_ram)
        
        self.toolbar.addSeparator()
        
        # Network signal strength
        self.lbl_wifi = QLabel("SIG: 100%")
        self.lbl_wifi.setStyleSheet("font-size: 11px; font-weight: 600; color: #00d2ff;")
        self.toolbar.addWidget(self.lbl_wifi)
        
        # Stretch spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # E-Stop Button
        self.btn_estop = QPushButton("EMERGENCY STOP")
        self.btn_estop.setObjectName("btn_estop") # triggers e-stop red layout
        self.btn_estop.clicked.connect(self.trigger_global_estop)
        self.toolbar.addWidget(self.btn_estop)

    def setup_sidebar(self):
        menu_items = [
            "Dashboard",
            "System Check",
            "Robot Connection",
            "SLAM Control",
            "3D Mapping (Lidar)",
            "Sensors Dashboard",
            "Camera Live Stream",
            "Motor Diagnostics",
            "Robot Control Deck",
            "Interactive Terminal",
            "Diagnostic Logs",
            "ROS Topic Explorer",
            "FastAPI Web Server",
            "Client SDK Center",
            "System Settings"
        ]
        self.sidebar.addItems(menu_items)
        self.sidebar.currentRowChanged.connect(self.sidebar_row_changed)
        
    def setup_workspace(self):
        # 15 Tab Pages allocation inside stacked widget in matching order
        self.tab_dashboard = TabDashboard()   # Index 0
        self.tab_preflight = TabPreflight()   # Index 1
        self.tab_connection = TabConnection() # Index 2
        self.tab_slam = TabSLAM()             # Index 3
        self.tab_pointcloud = TabPointCloud() # Index 4
        self.tab_sensors = TabSensors()       # Index 5
        self.tab_camera = TabCamera()         # Index 6
        self.tab_motor = TabMotor()           # Index 7
        self.tab_control = TabControl()       # Index 8
        self.tab_terminal = TabTerminal()     # Index 9
        self.tab_logging = TabLogging()       # Index 10
        self.tab_explorer = TabExplorer()     # Index 11
        self.tab_websocket = TabWebSocket()   # Index 12
        self.tab_api = TabAPI()               # Index 13
        self.tab_settings = TabSettings()     # Index 14
        
        self.workspace.addWidget(self.tab_dashboard)   # 0
        self.workspace.addWidget(self.tab_preflight)   # 1
        self.workspace.addWidget(self.tab_connection)  # 2
        self.workspace.addWidget(self.tab_slam)        # 3
        self.workspace.addWidget(self.tab_pointcloud)  # 4
        self.workspace.addWidget(self.tab_sensors)     # 5
        self.workspace.addWidget(self.tab_camera)      # 6
        self.workspace.addWidget(self.tab_motor)       # 7
        self.workspace.addWidget(self.tab_control)     # 8
        self.workspace.addWidget(self.tab_terminal)    # 9
        self.workspace.addWidget(self.tab_logging)     # 10
        self.workspace.addWidget(self.tab_explorer)    # 11
        self.workspace.addWidget(self.tab_websocket)   # 12
        self.workspace.addWidget(self.tab_api)         # 13
        self.workspace.addWidget(self.tab_settings)    # 14
        
        # Default display SLAM Mapping Console on launch
        self.sidebar.setCurrentRow(3)

    def setup_statusbar(self):
        self.lbl_ip = QLabel("ROBOT IP: Disconnected  |")
        self.status_bar.addWidget(self.lbl_ip)
        
        self.lbl_domain = QLabel("ROS DOMAIN ID: 0  |")
        self.status_bar.addWidget(self.lbl_domain)
        
        self.lbl_ping = QLabel("PING: - ms  |")
        self.status_bar.addWidget(self.lbl_ping)
        
        self.lbl_fps = QLabel("FPS: -  |")
        self.status_bar.addWidget(self.lbl_fps)
        
        self.lbl_msg = QLabel("Ready")
        self.status_bar.addWidget(self.lbl_msg)

    def sidebar_row_changed(self, row):
        self.workspace.setCurrentIndex(row)

    @pyqtSlot(dict)
    def on_telemetry_tick(self, data: dict):
        """Processes high frequency telemetry to refresh top toolbar metrics."""
        sys = data.get("system", {})
        cpu = sys.get("cpu", 0.0)
        ram = sys.get("ram", 0.0)
        ros = sys.get("ros_state", "Offline")
        slam = sys.get("slam_state", "Idle")
        net = sys.get("network_quality", 100)
        
        self.bar_cpu.setValue(int(cpu))
        self.bar_ram.setValue(int(ram))
        self.lbl_ros_state.setText(f"ROS: {ros.upper()}")
        self.lbl_slam_state.setText(f"SLAM: {slam.upper()}")
        self.lbl_wifi.setText(f"SIG: {net}%")
        
        bat = data.get("battery", {})
        self.bar_battery.setValue(int(bat.get("percentage", 100)))
        
        # Latency & ping
        # If simulated, set ping = 1ms
        if telemetry_bridge.simulated:
            self.lbl_ping.setText("PING: 1 ms  |")
            self.lbl_fps.setText("FPS: 30.0  |")
            self.lbl_ip.setText("ROBOT IP: 127.0.0.1  |")

    @pyqtSlot(bool, str)
    def on_ssh_status(self, connected: bool, msg: str):
        if connected:
            self.lbl_conn.setText("CONNECTED")
            self.lbl_conn.setStyleSheet("background-color: #00b4d8; color: #121214; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")
            active_p = db.get_active_profile()
            if active_p:
                self.lbl_ip.setText(f"ROBOT IP: {active_p['ip_address']}  |")
                self.lbl_domain.setText(f"ROS DOMAIN ID: {active_p['ros_domain_id']}  |")
        else:
            self.lbl_conn.setText("OFFLINE")
            self.lbl_conn.setStyleSheet("background-color: #e63946; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")
            self.lbl_ip.setText("ROBOT IP: Disconnected  |")
            self.lbl_ping.setText("PING: - ms  |")
            self.lbl_fps.setText("FPS: -  |")

    def measure_connection_health(self):
        """Triggers ping tests to active connection profile to show latency in statusbar."""
        if not ssh_manager.is_connected() or telemetry_bridge.simulated:
            return
            
        active_p = db.get_active_profile()
        if active_p:
            from app.core.network_troubleshooter import NetworkTroubleshooter
            res = NetworkTroubleshooter.ping_host(active_p["ip_address"], count=1)
            if res["success"]:
                self.lbl_ping.setText(f"PING: {res['latency']:.1f} ms  |")
            else:
                self.lbl_ping.setText("PING: TIMEOUT  |")

    def on_checklist_resolved(self, auto_connect=True):
        self.sidebar.setCurrentRow(2)
        if auto_connect:
            self.tab_connection.ip_input.setText("127.0.0.1")
            self.tab_connection.start_connection_wizard()

    def launch_slam_from_dashboard(self):
        self.sidebar.setCurrentRow(3)
        self.tab_slam.start_slam()

    def trigger_global_estop(self):
        # Stop robot motion immediately via the Control Deck E-stop method
        self.tab_control.emergency_stop()

    def closeEvent(self, event):
        # Safe termination of threads
        try:
            if hasattr(self, 'tab_camera') and self.tab_camera.thread.isRunning():
                self.tab_camera.thread.running = False
                self.tab_camera.thread.wait()
        except Exception:
            pass
            
        try:
            if hasattr(self, 'tab_control') and self.tab_control.gp_listener.isRunning():
                self.tab_control.gp_listener.stop()
        except Exception:
            pass

        telemetry_bridge.stop()
        ssh_manager.disconnect()
        self.ping_timer.stop()
        
        try:
            from app.core.web_api import api_server
            api_server.stop()
        except Exception:
            pass
            
        event.accept()
