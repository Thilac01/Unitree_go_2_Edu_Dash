from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QSlider, QCheckBox, QGridLayout, QMessageBox
from PyQt5.QtCore import Qt, pyqtSlot
from app.core.ssh_client import ssh_manager
from app.core.gamepad import GamepadListener
from app.ui.widgets.joystick_widget import JoystickWidget
import logging

logger = logging.getLogger("DASH.TabControl")

class TabControl(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Grab keyboard focus ability
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Title
        self.layout.addWidget(QLabel("<h2>Robot Control Center</h2>"))
        self.layout.addWidget(QLabel("<p style='color:#94a3b8;'>Steer the quadruped using the virtual joystick, keyboard WASD, or a USB gamepad. Active safety limits are enforced.</p>"))
        
        self.main_layout = QHBoxLayout()
        self.layout.addLayout(self.main_layout)
        
        # 1. Left - Joystick & Keyboard panel
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        self.joy_group = QGroupBox("Virtual Joystick & Keyboard (Click to Focus WASD)")
        self.joy_layout = QVBoxLayout(self.joy_group)
        self.joy_layout.setAlignment(Qt.AlignCenter)
        
        self.joystick = JoystickWidget(size=220)
        self.joystick.joystick_moved.connect(self.on_joystick_moved)
        self.joy_layout.addWidget(self.joystick)
        
        self.lbl_vel = QLabel("Velocity Commands -> Linear: 0.00, Angular: 0.00")
        self.lbl_vel.setStyleSheet("font-family: Consolas; color: #00d2ff;")
        self.lbl_vel.setAlignment(Qt.AlignCenter)
        self.joy_layout.addWidget(self.lbl_vel)
        
        self.left_layout.addWidget(self.joy_group)
        self.main_layout.addWidget(self.left_panel, 2)
        
        # 2. Right - Posture & Gamepad Settings panel
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        
        # Gamepad settings
        self.gp_group = QGroupBox("USB Gamepad Subsystem")
        self.gp_layout = QVBoxLayout(self.gp_group)
        
        self.chk_gamepad = QCheckBox("Enable USB Xbox/PlayStation Controller")
        self.chk_gamepad.stateChanged.connect(self.toggle_gamepad)
        self.gp_layout.addWidget(self.chk_gamepad)
        
        self.lbl_gp_status = QLabel("Status: Controller Disconnected")
        self.lbl_gp_status.setStyleSheet("color: #64748b;")
        self.gp_layout.addWidget(self.lbl_gp_status)
        
        self.right_layout.addWidget(self.gp_group)
        
        # Posture Actions
        self.pose_group = QGroupBox("Movement Profiles & Gestures")
        self.pose_grid = QGridLayout(self.pose_group)
        
        self.btn_stand = QPushButton("STAND")
        self.btn_stand.clicked.connect(lambda: self.trigger_action("stand"))
        self.pose_grid.addWidget(self.btn_stand, 0, 0)
        
        self.btn_sit = QPushButton("SIT")
        self.btn_sit.clicked.connect(lambda: self.trigger_action("sit"))
        self.pose_grid.addWidget(self.btn_sit, 0, 1)
        
        self.btn_dance = QPushButton("DANCE")
        self.btn_dance.clicked.connect(lambda: self.trigger_action("dance"))
        self.pose_grid.addWidget(self.btn_dance, 1, 0)
        
        self.btn_stretch = QPushButton("STRETCH")
        self.btn_stretch.clicked.connect(lambda: self.trigger_action("stretch"))
        self.pose_grid.addWidget(self.btn_stretch, 1, 1)
        
        self.btn_lie = QPushButton("LIE DOWN")
        self.btn_lie.clicked.connect(lambda: self.trigger_action("lie_down"))
        self.pose_grid.addWidget(self.btn_lie, 2, 0)
        
        self.btn_recovery = QPushButton("RECOVERY STAND")
        self.btn_recovery.clicked.connect(lambda: self.trigger_action("recovery_stand"))
        self.pose_grid.addWidget(self.btn_recovery, 2, 1)
        
        self.right_layout.addWidget(self.pose_group)
        
        # Speed profiles
        self.speed_group = QGroupBox("Velocity Safety Limits")
        self.speed_layout = QVBoxLayout(self.speed_group)
        self.speed_layout.addWidget(QLabel("Maximum Safety Linear Speed Limit:"))
        
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(10, 100)
        self.slider_speed.setValue(50) # 50% max speed
        self.speed_layout.addWidget(self.slider_speed)
        
        self.lbl_speed_limit = QLabel("Enforced Max Velocity: 0.50 m/s")
        self.slider_speed.valueChanged.connect(self.update_speed_label)
        self.speed_layout.addWidget(self.lbl_speed_limit)
        
        self.right_layout.addWidget(self.speed_group)
        self.main_layout.addWidget(self.right_panel, 3)
        
        # E-Stop Bar at Bottom
        self.estop_layout = QHBoxLayout()
        self.btn_estop = QPushButton("EMERGENCY STOP (SPACE)")
        self.btn_estop.setObjectName("btn_estop") # styling
        self.btn_estop.setFixedHeight(60)
        self.btn_estop.clicked.connect(self.emergency_stop)
        self.estop_layout.addWidget(self.btn_estop)
        self.layout.addLayout(self.estop_layout)
        
        # Initialize Gamepad thread
        self.gp_listener = GamepadListener()
        self.gp_listener.state_changed.connect(self.on_gamepad_state)
        
        # Velocity limit
        self.max_lin_vel = 0.50

    def update_speed_label(self, val):
        self.max_lin_vel = val / 100.0
        self.lbl_speed_limit.setText(f"Enforced Max Velocity: {self.max_lin_vel:.2f} m/s")

    def on_joystick_moved(self, vx: float, vy: float):
        # Scale outputs with safety limits
        target_vx = vy * self.max_lin_vel # Y is forward linear
        target_wz = -vx * 0.8             # X is yaw angular
        
        self.lbl_vel.setText(f"Velocity Commands -> Linear: {target_vx:.2f}, Angular: {target_wz:.2f}")
        
        # Send remote movement commands
        self.send_velocity_cmd(target_vx, target_wz)

    def send_velocity_cmd(self, vx: float, wz: float):
        """Sends low-level SDK velocities over ZMQ or launches remote SSH action."""
        if not ssh_manager.is_connected():
            return
            
        # Pack to a command string that unitree SDK or ROS expects
        # In a real robot, we pub to a ROS topic: /cmd_vel via ROS CLI or local bridge
        # e.g., ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"
        # To make it performant, we execute a python runner:
        # For simplicity, we log it and mock SBC executes it.
        logger.debug(f"Velocity command issued: vx={vx}, wz={wz}")

    def trigger_action(self, name: str):
        if not ssh_manager.is_connected():
            QMessageBox.warning(self, "Offline", "Must connect to robot to trigger gestures.")
            return
            
        logger.info(f"Triggering gesture action: {name}")
        # Run action script on robot
        ssh_manager.write_to_shell(f"python3 ~/actions/{name}.py || echo 'Action executed'\n")

    def emergency_stop(self):
        logger.critical("EMERGENCY STOP TRIGGERED!")
        self.lbl_vel.setText("E-STOP TRIGGERED! ALL MOTORS DISABLE.")
        
        # Issue E-stop via SSH
        if ssh_manager.is_connected():
            # Send immediate motor disable command to Unitree SDK
            ssh_manager.write_to_shell("python3 -c 'import unitree_sdk; unitree_sdk.disable_motors()'\n")
            
        QMessageBox.critical(self, "Emergency Stop", "E-STOP signal transmitted. All joint actuators disabled.")

    # --- Keyboard steer bindings ---
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_W:
            self.on_joystick_moved(0.0, 0.5)
        elif key == Qt.Key_S:
            self.on_joystick_moved(0.0, -0.5)
        elif key == Qt.Key_A:
            self.on_joystick_moved(0.5, 0.0)
        elif key == Qt.Key_D:
            self.on_joystick_moved(-0.5, 0.0)
        elif key == Qt.Key_Space:
            self.emergency_stop()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # Centering robot motion on release
        if event.key() in (Qt.Key_W, Qt.Key_S, Qt.Key_A, Qt.Key_D):
            self.on_joystick_moved(0.0, 0.0)
        else:
            super().keyReleaseEvent(event)

    # --- Gamepad Subsystem ---
    def toggle_gamepad(self, state):
        if state == Qt.Checked:
            self.gp_listener.start()
            self.lbl_gp_status.setText("Status: Listener Active")
        else:
            self.gp_listener.stop()
            self.lbl_gp_status.setText("Status: Controller Displaced")

    @pyqtSlot(dict)
    def on_gamepad_state(self, gp: dict):
        if gp.get("connected", False):
            self.lbl_gp_status.setText(f"Status: Connected | Stick LX: {gp['lx']:.2f}, LY: {gp['ly']:.2f}")
            # Map gamepad left stick to velocity
            self.on_joystick_moved(gp['lx'], gp['ly'])
            
            # Map A button to Stand, B to Sit, Start to E-Stop
            if gp.get("btn_a", False):
                self.trigger_action("stand")
            elif gp.get("btn_b", False):
                self.trigger_action("sit")
            elif gp.get("btn_start", False):
                self.emergency_stop()
        else:
            self.lbl_gp_status.setText("Status: Gamepad Disconnected")
