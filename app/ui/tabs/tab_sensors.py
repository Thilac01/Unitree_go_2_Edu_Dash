import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QProgressBar
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QColor, QFont
import pyqtgraph as pg
from app.core.telemetry_bridge import telemetry_bridge
import numpy as np

class TabSensors(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Main layout: Horizontal split
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # ----------------------------------------------------
        # Left Panel - Scrollable Categorized Telemetry Details
        # ----------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 5, 0)
        self.left_layout.setSpacing(15)
        
        # Category 1: System Health
        self.group_sys = QGroupBox("System & Link Diagnostics")
        self.grid_sys = QGridLayout(self.group_sys)
        self.grid_sys.setContentsMargins(10, 15, 10, 10)
        self.grid_sys.setSpacing(8)
        
        self.grid_sys.addWidget(QLabel("Onboard CPU Load:"), 0, 0)
        self.bar_cpu = QProgressBar()
        self.bar_cpu.setRange(0, 100)
        self.bar_cpu.setStyleSheet("QProgressBar { border: 1px solid #2d2d34; border-radius: 4px; background: #121214; text-align: center; font-size: 10px; height: 16px; } QProgressBar::chunk { background: #00b4d8; }")
        self.grid_sys.addWidget(self.bar_cpu, 0, 1)
        
        self.grid_sys.addWidget(QLabel("Memory Usage:"), 1, 0)
        self.bar_ram = QProgressBar()
        self.bar_ram.setRange(0, 100)
        self.bar_ram.setStyleSheet("QProgressBar { border: 1px solid #2d2d34; border-radius: 4px; background: #121214; text-align: center; font-size: 10px; height: 16px; } QProgressBar::chunk { background: #00ffcc; }")
        self.grid_sys.addWidget(self.bar_ram, 1, 1)
        
        self.lbl_sbc_temp = QLabel("SBC Temp: N/A")
        self.lbl_sbc_temp.setStyleSheet("color: #e2e8f0; font-weight: 500;")
        self.grid_sys.addWidget(self.lbl_sbc_temp, 2, 0)
        
        self.lbl_wifi_sig = QLabel("Link Quality: N/A")
        self.lbl_wifi_sig.setStyleSheet("color: #e2e8f0; font-weight: 500;")
        self.grid_sys.addWidget(self.lbl_wifi_sig, 2, 1)
        
        self.left_layout.addWidget(self.group_sys)
        
        # Category 2: IMU Metrics
        self.group_imu = QGroupBox("IMU & Attitude Indicators")
        self.grid_imu = QGridLayout(self.group_imu)
        self.grid_imu.setContentsMargins(10, 15, 10, 10)
        self.grid_imu.setSpacing(8)
        
        self.lbl_roll = QLabel("Roll Angle: 0.0°")
        self.lbl_pitch = QLabel("Pitch Angle: 0.0°")
        self.lbl_yaw = QLabel("Yaw Angle: 0.0°")
        self.grid_imu.addWidget(self.lbl_roll, 0, 0)
        self.grid_imu.addWidget(self.lbl_pitch, 0, 1)
        self.grid_imu.addWidget(self.lbl_yaw, 0, 2)
        
        self.lbl_accel = QLabel("Accel (X, Y, Z): 0.00, 0.00, 9.81 m/s²")
        self.lbl_gyro = QLabel("Gyro (X, Y, Z): 0.00, 0.00, 0.00 rad/s")
        self.grid_imu.addWidget(self.lbl_accel, 1, 0, 1, 3)
        self.grid_imu.addWidget(self.lbl_gyro, 2, 0, 1, 3)
        
        self.left_layout.addWidget(self.group_imu)
        
        # Category 3: GPS Positioning
        self.group_gps = QGroupBox("GPS Positioning & Satellites")
        self.grid_gps = QGridLayout(self.group_gps)
        self.grid_gps.setContentsMargins(10, 15, 10, 10)
        self.grid_gps.setSpacing(8)
        
        self.lbl_gps_lat = QLabel("Latitude: 0.000000°")
        self.lbl_gps_lon = QLabel("Longitude: 0.000000°")
        self.lbl_gps_alt = QLabel("Altitude: 0.0m")
        self.lbl_gps_speed = QLabel("Speed: 0.0 m/s")
        self.lbl_gps_heading = QLabel("Heading: 0.0°")
        self.lbl_gps_sats = QLabel("Satellites: 0")
        
        self.grid_gps.addWidget(self.lbl_gps_lat, 0, 0)
        self.grid_gps.addWidget(self.lbl_gps_lon, 0, 1)
        self.grid_gps.addWidget(self.lbl_gps_alt, 1, 0)
        self.grid_gps.addWidget(self.lbl_gps_speed, 1, 1)
        self.grid_gps.addWidget(self.lbl_gps_heading, 2, 0)
        self.grid_gps.addWidget(self.lbl_gps_sats, 2, 1)
        
        self.left_layout.addWidget(self.group_gps)
        
        # Category 4: Battery & Power
        self.group_bat = QGroupBox("Battery & Power Subsystem")
        self.grid_bat = QGridLayout(self.group_bat)
        self.grid_bat.setContentsMargins(10, 15, 10, 10)
        self.grid_bat.setSpacing(8)
        
        self.lbl_bat_pct = QLabel("Capacity: 100%")
        self.lbl_bat_volt = QLabel("Voltage: 24.0V")
        self.lbl_bat_curr = QLabel("Current: 0.0A")
        self.lbl_bat_temp = QLabel("Temp: 25.0°C")
        self.lbl_bat_health = QLabel("Health: 100%")
        
        self.grid_bat.addWidget(self.lbl_bat_pct, 0, 0)
        self.grid_bat.addWidget(self.lbl_bat_volt, 0, 1)
        self.grid_bat.addWidget(self.lbl_bat_curr, 1, 0)
        self.grid_bat.addWidget(self.lbl_bat_temp, 1, 1)
        self.grid_bat.addWidget(self.lbl_bat_health, 2, 0)
        
        self.left_layout.addWidget(self.group_bat)
        
        # Category 5: Motors Summary Table
        self.group_motors = QGroupBox("Joint Actuators Quick Status")
        self.layout_motors = QVBoxLayout(self.group_motors)
        self.layout_motors.setContentsMargins(8, 15, 8, 8)
        
        self.motor_table = QTableWidget()
        self.motor_table.setColumnCount(4)
        self.motor_table.setHorizontalHeaderLabels(["Joint", "Torque (N·m)", "Temp (°C)", "Current (A)"])
        self.motor_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.motor_table.verticalHeader().setVisible(False)
        self.motor_table.setRowCount(12)
        self.motor_table.setMinimumHeight(240)
        self.motor_table.setStyleSheet("QTableWidget { font-size: 11px; }")
        
        self.joint_names = {
            0: "FR Hip Roll", 1: "FR Hip Pitch", 2: "FR Knee Pitch",
            3: "FL Hip Roll", 4: "FL Hip Pitch", 5: "FL Knee Pitch",
            6: "RR Hip Roll", 7: "RR Hip Pitch", 8: "RR Knee Pitch",
            9: "RL Hip Roll", 10: "RL Hip Pitch", 11: "RL Knee Pitch"
        }
        for i in range(12):
            self.motor_table.setItem(i, 0, QTableWidgetItem(f"{self.joint_names[i]}"))
            for col in range(1, 4):
                self.motor_table.setItem(i, col, QTableWidgetItem("0.0"))
                
        self.layout_motors.addWidget(self.motor_table)
        self.left_layout.addWidget(self.group_motors)
        
        self.scroll_area.setWidget(self.left_container)
        self.main_layout.addWidget(self.scroll_area, 2)
        
        # ----------------------------------------------------
        # Right Panel - Live Lidar stream list & Attitude Plot
        # ----------------------------------------------------
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(10)
        
        # Group 1: Live Lidar Point Stream
        self.group_lidar = QGroupBox("Raw Lidar Point Stream (x, y, z, time, density)")
        self.layout_lidar = QVBoxLayout(self.group_lidar)
        self.layout_lidar.setContentsMargins(8, 15, 8, 8)
        
        self.lidar_table = QTableWidget()
        self.lidar_table.setColumnCount(6)
        self.lidar_table.setHorizontalHeaderLabels(["ID", "X (m)", "Y (m)", "Z (m)", "Time (s)", "Density"])
        self.lidar_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lidar_table.verticalHeader().setVisible(False)
        self.lidar_table.setRowCount(30)
        self.lidar_table.setMinimumHeight(220)
        self.lidar_table.setStyleSheet("QTableWidget { font-size: 11px; font-family: Consolas, monospace; }")
        
        for i in range(30):
            for col in range(6):
                self.lidar_table.setItem(i, col, QTableWidgetItem("-"))
                
        self.layout_lidar.addWidget(self.lidar_table)
        self.right_layout.addWidget(self.group_lidar, 3)
        
        # Group 2: Attitude Trend Graph
        self.group_graph = QGroupBox("Real-Time Attitude Roll-Pitch-Yaw Trends")
        self.layout_graph = QVBoxLayout(self.group_graph)
        self.layout_graph.setContentsMargins(8, 15, 8, 8)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1a1a1e")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.addLegend()
        self.plot_widget.setLabel('left', 'Attitude', units='deg')
        self.plot_widget.setLabel('bottom', 'Time Steps')
        
        self.curve_roll = self.plot_widget.plot(pen=pg.mkPen('#00b4d8', width=2), name="Roll")
        self.curve_pitch = self.plot_widget.plot(pen=pg.mkPen('#ff9f1c', width=2), name="Pitch")
        self.curve_yaw = self.plot_widget.plot(pen=pg.mkPen('#00ffcc', width=2), name="Yaw")
        self.layout_graph.addWidget(self.plot_widget)
        
        self.right_layout.addWidget(self.group_graph, 2)
        self.main_layout.addWidget(self.right_container, 3)
        
        # Plot data queues
        self.max_pts = 150
        self.roll_data = []
        self.pitch_data = []
        self.yaw_data = []
        
        # Bind telemetry
        telemetry_bridge.telemetry_received.connect(self.on_telemetry_received)
        telemetry_bridge.pointcloud_received.connect(self.on_points_received)

    @pyqtSlot(dict)
    def on_telemetry_received(self, data: dict):
        # 1. System Load
        sys = data.get("system", {})
        self.bar_cpu.setValue(int(sys.get("cpu", 0.0)))
        self.bar_ram.setValue(int(sys.get("ram", 0.0)))
        
        temp = sys.get("temperature", 0.0)
        self.lbl_sbc_temp.setText(f"SBC Temp: {temp:.1f}°C")
        if temp > 65.0:
            self.lbl_sbc_temp.setStyleSheet("color: #e63946; font-weight: bold;")
        else:
            self.lbl_sbc_temp.setStyleSheet("color: #e2e8f0; font-weight: 500;")
            
        self.lbl_wifi_sig.setText(f"Link Quality: {sys.get('network_quality', 100)}%")
        
        # 2. IMU attitude
        imu = data.get("imu", {})
        roll = imu.get("roll", 0.0)
        pitch = imu.get("pitch", 0.0)
        yaw = imu.get("yaw", 0.0)
        
        self.lbl_roll.setText(f"Roll Angle: {roll:.1f}°")
        self.lbl_pitch.setText(f"Pitch Angle: {pitch:.1f}°")
        self.lbl_yaw.setText(f"Yaw Angle: {yaw:.1f}°")
        self.lbl_accel.setText(f"Accel (X, Y, Z): {imu.get('accel_x',0.0):.2f}, {imu.get('accel_y',0.0):.2f}, {imu.get('accel_z',9.81):.2f} m/s²")
        self.lbl_gyro.setText(f"Gyro (X, Y, Z): {imu.get('gyro_x',0.0):.3f}, {imu.get('gyro_y',0.0):.3f}, {imu.get('gyro_z',0.0):.3f} rad/s")
        
        # 3. GPS
        gps = data.get("gps", {})
        self.lbl_gps_lat.setText(f"Latitude: {gps.get('latitude', 0.0):.6f}°")
        self.lbl_gps_lon.setText(f"Longitude: {gps.get('longitude', 0.0):.6f}°")
        self.lbl_gps_alt.setText(f"Altitude: {gps.get('altitude', 0.0):.1f}m")
        self.lbl_gps_speed.setText(f"Speed: {gps.get('speed', 0.0):.1f} m/s")
        self.lbl_gps_heading.setText(f"Heading: {gps.get('heading', 0.0):.1f}°")
        self.lbl_gps_sats.setText(f"Satellites: {gps.get('satellites', 0)}")
        
        # 4. Battery
        bat = data.get("battery", {})
        bat_pct = bat.get("percentage", 100)
        self.lbl_bat_pct.setText(f"Capacity: {bat_pct}%")
        if bat_pct < 20:
            self.lbl_bat_pct.setStyleSheet("color: #e63946; font-weight: bold;")
        else:
            self.lbl_bat_pct.setStyleSheet("color: #e2e8f0; font-weight: 500;")
        self.lbl_bat_volt.setText(f"Voltage: {bat.get('voltage', 24.0):.1f}V")
        self.lbl_bat_curr.setText(f"Current: {bat.get('current', 0.0):.2f}A")
        self.lbl_bat_temp.setText(f"Temp: {bat.get('temperature', 25.0):.1f}°C")
        self.lbl_bat_health.setText(f"Health: {bat.get('health', 100)}%")
        
        # 5. Motors table
        motors = data.get("motors", [])
        for i in range(min(12, len(motors))):
            m = motors[i]
            tq = m.get("torque", 0.0)
            tmp = m.get("temperature", 30.0)
            cur = m.get("current", 0.0)
            
            # Torque
            item_tq = self.motor_table.item(i, 1)
            if item_tq:
                item_tq.setText(f"{tq:.2f}")
            # Temp
            item_tmp = self.motor_table.item(i, 2)
            if item_tmp:
                item_tmp.setText(f"{tmp:.1f}")
                if tmp > 60.0:
                    item_tmp.setForeground(QColor("#e63946"))
                elif tmp > 45.0:
                    item_tmp.setForeground(QColor("#ff9f1c"))
                else:
                    item_tmp.setForeground(QColor("#ffffff"))
            # Current
            item_cur = self.motor_table.item(i, 3)
            if item_cur:
                item_cur.setText(f"{cur:.2f}")
                
        # 6. Attitude Trend queues
        self.roll_data.append(roll)
        self.pitch_data.append(pitch)
        self.yaw_data.append(yaw)
        
        if len(self.roll_data) > self.max_pts:
            self.roll_data.pop(0)
            self.pitch_data.pop(0)
            self.yaw_data.pop(0)
            
        self.curve_roll.setData(self.roll_data)
        self.curve_pitch.setData(self.pitch_data)
        self.curve_yaw.setData(self.yaw_data)

    @pyqtSlot(np.ndarray)
    def on_points_received(self, points: np.ndarray):
        """Callback to populate the raw numerical Lidar points table."""
        if points is None or points.size == 0:
            return
            
        # points shape: Nx5 (x, y, z, time_offset, density)
        num_rows = min(30, points.shape[0])
        for i in range(num_rows):
            pt = points[i]
            x, y, z = pt[0], pt[1], pt[2]
            
            t_val = pt[3] if len(pt) > 3 else 0.0
            d_val = pt[4] if len(pt) > 4 else 0.0
            
            # Update columns
            # ID
            self.lidar_table.item(i, 0).setText(str(i))
            # X
            self.lidar_table.item(i, 1).setText(f"{x:.3f}")
            # Y
            self.lidar_table.item(i, 2).setText(f"{y:.3f}")
            # Z
            self.lidar_table.item(i, 3).setText(f"{z:.3f}")
            # Time
            self.lidar_table.item(i, 4).setText(f"{t_val:.4f}")
            # Density
            self.lidar_table.item(i, 5).setText(f"{d_val:.1f}")
