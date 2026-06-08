import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QSlider, QCheckBox, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSlot
from app.core.telemetry_bridge import telemetry_bridge
from app.ui.widgets.pointcloud_widget import PointCloudWidget
import numpy as np

class TabPointCloud(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        
        # 1. Left Viewport
        self.viewer_widget = PointCloudWidget()
        self.layout.addWidget(self.viewer_widget, 4)
        
        # 2. Right Control Panel
        self.ctrl_panel = QWidget()
        self.ctrl_layout = QVBoxLayout(self.ctrl_panel)
        self.ctrl_layout.setContentsMargins(5, 0, 0, 0)
        
        # Stats Group
        self.stats_group = QGroupBox("Cloud Telemetry")
        self.stats_layout = QVBoxLayout(self.stats_group)
        self.lbl_points = QLabel("Point Count: 0")
        self.stats_layout.addWidget(self.lbl_points)
        self.lbl_density = QLabel("Density: 0.0 pts/m³")
        self.stats_layout.addWidget(self.lbl_density)
        self.lbl_fps = QLabel("Update Rate: 0.0 Hz")
        self.stats_layout.addWidget(self.lbl_fps)
        self.lbl_size = QLabel("Memory Size: 0 KB")
        self.stats_layout.addWidget(self.lbl_size)
        self.ctrl_layout.addWidget(self.stats_group)
        
        # View Controls
        self.view_group = QGroupBox("View Settings")
        self.view_layout = QVBoxLayout(self.view_group)
        
        self.chk_grid = QCheckBox("Show Ground Grid")
        self.chk_grid.setChecked(True)
        self.chk_grid.stateChanged.connect(self.toggle_grid)
        self.view_layout.addWidget(self.chk_grid)
        
        self.chk_filter = QCheckBox("Enable Voxel Downsample")
        self.chk_filter.setChecked(False)
        self.view_layout.addWidget(self.chk_filter)
        
        self.view_layout.addWidget(QLabel("Point Size:"))
        self.slider_size = QSlider(Qt.Horizontal)
        self.slider_size.setRange(1, 10)
        self.slider_size.setValue(3)
        self.slider_size.valueChanged.connect(self.change_point_size)
        self.view_layout.addWidget(self.slider_size)
        
        self.btn_reset = QPushButton("Reset Camera View")
        self.btn_reset.clicked.connect(self.viewer_widget.reset_view)
        self.view_layout.addWidget(self.btn_reset)
        
        self.ctrl_layout.addWidget(self.view_group)
        
        # Export Actions
        self.export_group = QGroupBox("Export Cloud")
        self.export_layout = QVBoxLayout(self.export_group)
        
        self.btn_export = QPushButton("Export PLY File")
        self.btn_export.setObjectName("btn_save")
        self.btn_export.clicked.connect(self.export_ply)
        self.export_layout.addWidget(self.btn_export)
        
        self.ctrl_layout.addWidget(self.export_group)
        self.ctrl_layout.addStretch()
        
        self.layout.addWidget(self.ctrl_panel, 1)
        
        # Frame rate estimation variables
        self.last_update_time = time.time()
        self.fps_filter = 0.0
        self.latest_points = None
        
        # Telemetry bindings
        telemetry_bridge.pointcloud_received.connect(self.on_points_received)

    @pyqtSlot(np.ndarray)
    def on_points_received(self, points: np.ndarray):
        """Processes and filters point clouds on reception."""
        if points is None or points.size == 0:
            return
            
        t_now = time.time()
        dt = t_now - self.last_update_time
        self.last_update_time = t_now
        
        # Low pass filter for FPS
        fps = 1.0 / dt if dt > 0 else 0.0
        self.fps_filter = 0.9 * self.fps_filter + 0.1 * fps
        
        # Optional voxel downsampling via simple NumPy slicing (striding)
        # to ensure CPU efficiency on Windows without complex Open3D compiling
        processed_points = points
        if self.chk_filter.isChecked():
            # Slice step of 4 (takes 1/4th of points)
            processed_points = points[::4]
            
        self.latest_points = processed_points
        self.viewer_widget.update_points(processed_points)
        
        # Update UI stats labels
        cnt = processed_points.shape[0]
        self.lbl_points.setText(f"Point Count: {cnt}")
        self.lbl_fps.setText(f"Update Rate: {self.fps_filter:.1f} Hz")
        self.lbl_density.setText(f"Density: {cnt / 250.0:.1f} pts/m³")
        self.lbl_size.setText(f"Memory Size: {processed_points.nbytes / 1024:.1f} KB")

    def toggle_grid(self, state):
        if self.viewer_widget.initialized:
            if state == Qt.Checked:
                self.viewer_widget.gl_widget.addItem(self.viewer_widget.grid)
            else:
                self.viewer_widget.gl_widget.removeItem(self.viewer_widget.grid)

    def change_point_size(self, val):
        if self.viewer_widget.initialized:
            self.viewer_widget.scatter.setData(size=val)

    def export_ply(self):
        if self.latest_points is None:
            QMessageBox.warning(self, "No Data", "No pointcloud telemetry received yet.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export Point Cloud", "pointcloud_export.ply", "PLY Files (*.ply)")
        if path:
            try:
                # Format ply header
                header = f"""ply
format ascii 1.0
element vertex {self.latest_points.shape[0]}
property float x
property float y
property float z
end_header
"""
                with open(path, "w") as f:
                    f.write(header)
                    for pt in self.latest_points:
                        f.write(f"{pt[0]:.4f} {pt[1]:.4f} {pt[2]:.4f}\n")
                QMessageBox.information(self, "Export Complete", f"Point cloud successfully written to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to save PLY file: {e}")
