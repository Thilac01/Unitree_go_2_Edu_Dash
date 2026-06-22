from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QGridLayout, QTextBrowser, QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import QTimer, pyqtSlot, Qt
from app.core.ssh_client import ssh_manager
from app.core.telemetry_bridge import telemetry_bridge
from app.ui.widgets.pointcloud_widget import PointCloudWidget
import numpy as np

class TabSLAM(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Title Header
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 5)
        title_lbl = QLabel("<h2>SLAM Control & RViz Mapping Console</h2>")
        desc_lbl = QLabel("<p style='color:#94a3b8; margin-left: 15px;'>Orchestrate onboard Lidar SLAM nodes and interact with the 3D grid and occupancy map layer.</p>")
        h_layout.addWidget(title_lbl)
        h_layout.addWidget(desc_lbl)
        h_layout.addStretch()
        self.layout.addWidget(header)
        
        # Instantiate large 3D viewport widget first
        self.viewer_widget = PointCloudWidget()
        
        # 1. Left Displays Tree Widget (RViz Style Checklist)
        self.display_tree = QTreeWidget()
        self.display_tree.setHeaderLabels(["Display Layer", "Status"])
        self.display_tree.setColumnCount(2)
        self.display_tree.setColumnWidth(0, 160)
        self.display_tree.setStyleSheet("QTreeWidget { background-color: #1a1a1e; border: 1px solid #2d2d34; border-radius: 6px; }")
        
        layers = [
            ("Grid", True),
            ("Robot Axes", True),
            ("Robot Model", True),
            ("Lidar Point Cloud", True),
            ("Occupancy Grid Map", True),
            ("Trajectory Path", True)
        ]
        
        self.tree_items = {}
        for name, checked in layers:
            item = QTreeWidgetItem(self.display_tree)
            item.setText(0, name)
            item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            item.setText(1, "Active" if checked else "Disabled")
            self.tree_items[name] = item
            
        # Add visual sub-properties for realism matching RViz config
        # Grid Sub-properties
        size_item = QTreeWidgetItem(self.tree_items["Grid"])
        size_item.setText(0, "  Size")
        size_item.setText(1, "30m x 30m")
        spacing_item = QTreeWidgetItem(self.tree_items["Grid"])
        spacing_item.setText(0, "  Spacing")
        spacing_item.setText(1, "1.0m")
        
        # Axes Sub-properties
        axes_len = QTreeWidgetItem(self.tree_items["Robot Axes"])
        axes_len.setText(0, "  Axis Length")
        axes_len.setText(1, "1.5m")
        
        # Model Sub-properties
        model_sz = QTreeWidgetItem(self.tree_items["Robot Model"])
        model_sz.setText(0, "  Box Volume")
        model_sz.setText(1, "0.6 x 0.4 x 0.25")
        
        # Point Cloud Sub-properties
        pc_topic = QTreeWidgetItem(self.tree_items["Lidar Point Cloud"])
        pc_topic.setText(0, "  Topic")
        pc_topic.setText(1, "/utlidar/cloud")
        pc_style = QTreeWidgetItem(self.tree_items["Lidar Point Cloud"])
        pc_style.setText(0, "  Color Style")
        pc_style.setText(1, "Height Map")
        
        # Map Sub-properties
        map_topic = QTreeWidgetItem(self.tree_items["Occupancy Grid Map"])
        map_topic.setText(0, "  Topic")
        map_topic.setText(1, "/map")
        map_alpha = QTreeWidgetItem(self.tree_items["Occupancy Grid Map"])
        map_alpha.setText(0, "  Translucent")
        map_alpha.setText(1, "True")
        
        # Trajectory Sub-properties
        traj_topic = QTreeWidgetItem(self.tree_items["Trajectory Path"])
        traj_topic.setText(0, "  Topic")
        traj_topic.setText(1, "/odom")
        traj_color = QTreeWidgetItem(self.tree_items["Trajectory Path"])
        traj_color.setText(0, "  Color")
        traj_color.setText(1, "Orange")
        
        self.display_tree.expandAll()
        self.display_tree.itemChanged.connect(self.on_layer_changed)
        
        # Main Splitter Layout (Horizontal Splitter containing Displays, Viewport, Control Panel)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.main_splitter)
        
        # Column 1: Left Displays Panel
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 5, 0)
        self.left_layout.addWidget(QLabel("<b>Displays Layer Tree</b>"))
        self.left_layout.addWidget(self.display_tree)
        
        self.btn_reset_view = QPushButton("Reset Viewport")
        self.btn_reset_view.clicked.connect(self.viewer_widget.reset_view)
        self.left_layout.addWidget(self.btn_reset_view)
        self.main_splitter.addWidget(self.left_panel)
        
        # Column 2: Center Viewport
        self.main_splitter.addWidget(self.viewer_widget)
        
        # Column 3: Right Control Panel
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(5, 0, 0, 0)
        
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_layout.addWidget(self.right_splitter)
        
        # Commands & Indicators (Top of Right Panel)
        self.control_box = QWidget()
        self.control_box_layout = QVBoxLayout(self.control_box)
        self.control_box_layout.setContentsMargins(0, 0, 0, 0)
        
        # SLAM Actions
        self.action_group = QGroupBox("SLAM Node Controller")
        self.action_grid = QGridLayout(self.action_group)
        self.action_grid.setSpacing(6)
        
        self.btn_start = QPushButton("Start SLAM")
        self.btn_start.setObjectName("btn_start_slam")
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
        
        self.control_box_layout.addWidget(self.action_group)
        
        # SLAM Telemetry Monitor Card
        self.telemetry_group = QGroupBox("Mapping Indicators")
        self.telemetry_grid = QGridLayout(self.telemetry_group)
        
        self.lbl_status = QLabel("SLAM STATUS: IDLE")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #64748b;")
        self.telemetry_grid.addWidget(self.lbl_status, 0, 0, 1, 2)
        
        self.lbl_closures = QLabel("Loop Closures: 0")
        self.telemetry_grid.addWidget(self.lbl_closures, 1, 0)
        
        self.lbl_points = QLabel("Point Count: 0")
        self.telemetry_grid.addWidget(self.lbl_points, 1, 1)
        
        self.lbl_confidence = QLabel("Confidence: 0.0%")
        self.telemetry_grid.addWidget(self.lbl_confidence, 2, 0)
        
        self.lbl_runtime = QLabel("Runtime: 0.0s")
        self.telemetry_grid.addWidget(self.lbl_runtime, 2, 1)
        
        self.control_box_layout.addWidget(self.telemetry_group)
        self.right_splitter.addWidget(self.control_box)
        
        # Remote process logs terminal (Bottom of Right Panel)
        self.log_group = QGroupBox("Remote Command Output")
        self.log_layout = QVBoxLayout(self.log_group)
        self.log_console = QTextBrowser()
        self.log_console.append("SLAM engine is currently offline. Press 'Start SLAM' to launch nodes.")
        self.log_layout.addWidget(self.log_console)
        self.right_splitter.addWidget(self.log_group)
        
        # Splitter sizing
        self.right_splitter.setSizes([350, 250])
        self.main_splitter.addWidget(self.right_panel)
        
        # Set panel sizing (Displays=220px, Viewport=800px, Controls=300px)
        self.main_splitter.setSizes([220, 800, 300])
        
        # Subscriptions
        telemetry_bridge.telemetry_received.connect(self.on_telemetry)
        telemetry_bridge.pointcloud_received.connect(self.on_points_received)

    @pyqtSlot(dict)
    def on_telemetry(self, data: dict):
        slam = data.get("slam", {})
        status = slam.get("status", "Idle")
        
        self.lbl_status.setText(f"SLAM STATUS: {status.upper()}")
        if status.lower() in ["mapping", "localizing", "running"]:
            self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #00b4d8;")
        else:
            self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #64748b;")
            
        self.lbl_closures.setText(f"Loop Closures: {slam.get('loop_closures', 0)}")
        self.lbl_points.setText(f"Point Count: {slam.get('point_count', 0)}")
        self.lbl_confidence.setText(f"Confidence: {slam.get('confidence', 0.0):.1f}%")
        self.lbl_runtime.setText(f"Runtime: {slam.get('runtime', 0.0):.1f}s")
        
        # Update 3D trajectory line strip
        trajectory = slam.get("trajectory", [])
        if trajectory:
            self.viewer_widget.update_trajectory(trajectory)
            # Use last trajectory point as current robot coordinates (x, y)
            latest_pos = trajectory[-1]
            imu = data.get("imu", {})
            yaw = imu.get("yaw", 0.0)
            self.viewer_widget.update_robot_pose(latest_pos[0], latest_pos[1], yaw)
            
        # Update Occupancy Grid map overlay if present
        if "map" in data:
            m = data["map"]
            # Reconstruct map matrix from flat JSON structure
            grid = np.array(m["data"], dtype=np.int8).reshape(m["width"], m["height"])
            self.viewer_widget.update_map(grid, m["resolution"], m["origin_x"], m["origin_y"])

    @pyqtSlot(np.ndarray)
    def on_points_received(self, points: np.ndarray):
        """Updates the 3D SLAM map viewer widget."""
        if points is not None and points.size > 0:
            self.viewer_widget.update_points(points)

    def on_layer_changed(self, item, column):
        if column != 0:
            return
        name = item.text(0)
        checked = item.checkState(0) == Qt.Checked
        item.setText(1, "Active" if checked else "Disabled")
        
        if name == "Grid":
            self.viewer_widget.toggle_grid(checked)
        elif name == "Robot Axes":
            self.viewer_widget.toggle_axes(checked)
        elif name == "Robot Model":
            self.viewer_widget.toggle_model(checked)
        elif name == "Lidar Point Cloud":
            self.viewer_widget.toggle_scatter(checked)
        elif name == "Occupancy Grid Map":
            self.viewer_widget.toggle_map(checked)
        elif name == "Trajectory Path":
            self.viewer_widget.toggle_trajectory(checked)

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

