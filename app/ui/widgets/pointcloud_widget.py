import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QVector3D
import numpy as np

logger = logging.getLogger("DASH.PointCloudWidget")

try:
    import pyqtgraph.opengl as gl
    OPENGL_AVAILABLE = True
except Exception as e:
    OPENGL_AVAILABLE = False
    logger.warning(f"PyQtGraph OpenGL module not loaded (PyOpenGL missing): {e}")

class PointCloudWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        if OPENGL_AVAILABLE:
            try:
                self.gl_widget = gl.GLViewWidget()
                self.layout.addWidget(self.gl_widget)
                
                # Set camera parameters
                self.gl_widget.opts['distance'] = 12
                self.gl_widget.opts['elevation'] = 30
                self.gl_widget.opts['azimuth'] = 45
                
                # Ground Grid
                self.grid = gl.GLGridItem()
                self.grid.setSize(30, 30)
                self.grid.setSpacing(1, 1)
                self.gl_widget.addItem(self.grid)
                
                # Cartesian Coordinate Axes (Red = X, Green = Y, Blue = Z)
                self.axes = gl.GLAxisItem()
                self.axes.setSize(1.5, 1.5, 1.5)
                self.gl_widget.addItem(self.axes)
                
                # Occupancy Grid Map overlay (rendered as a textured quad slightly below grid)
                self.map_image = gl.GLImageItem(data=np.zeros((2, 2, 4), dtype=np.uint8))
                self.gl_widget.addItem(self.map_image)
                
                # Robot Model bounding box (representing robot frame)
                # GLBoxItem.setSize() internally calls size.x(), size.y(), size.z()
                # so we MUST pass QVector3D, not a numpy array.
                self.robot_box = gl.GLBoxItem(
                    size=QVector3D(0.6, 0.4, 0.25),
                    color=(0, 255, 204, 128)   # Neon cyan semi-transparent (RGBA 0-255)
                )
                self.gl_widget.addItem(self.robot_box)
                
                # Scatter plot item for the Lidar point cloud
                self.scatter = gl.GLScatterPlotItem(
                    pos=np.zeros((1, 3)), 
                    color=(0.0, 0.7, 1.0, 0.8), 
                    size=2.5, 
                    pxMode=True
                )
                self.gl_widget.addItem(self.scatter)
                
                # Trajectory line to visualize SLAM path
                self.trajectory_line = gl.GLLinePlotItem(
                    pos=np.zeros((1, 3)),
                    color=(1.0, 0.62, 0.11, 1.0),  # Bright Orange
                    width=3.0,
                    mode='line_strip'
                )
                self.gl_widget.addItem(self.trajectory_line)
                
                self.initialized = True
            except Exception as ex:
                self.initialized = False
                logger.error(f"Failed to initialize GLViewWidget: {ex}")
                self._show_fallback_label(f"OpenGL Initialisation Failed: {ex}")
        else:
            self.initialized = False
            self._show_fallback_label("3D Rendering Unavailable. Please install PyOpenGL:\npip install PyOpenGL PyOpenGL-accelerate")

    def _show_fallback_label(self, msg: str):
        lbl = QLabel(msg)
        lbl.setStyleSheet("color: #e63946; font-size: 14px; font-weight: bold; background-color: #0b0b0d; border: 1px solid #2d2d34; border-radius: 6px;")
        lbl.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(lbl)

    def update_points(self, points: np.ndarray):
        """Updates the 3D scatter item with new points (Nx3 float32 array)."""
        if not self.initialized:
            return
            
        try:
            if points is None or points.size == 0:
                return
                
            # Compute colors based on height (Z value) for visual polish
            z_vals = points[:, 2]
            z_min, z_max = z_vals.min(), z_vals.max()
            
            # Avoid division by zero
            z_range = (z_max - z_min) if (z_max - z_min) > 0.01 else 1.0
            norm_z = (z_vals - z_min) / z_range
            
            # Color map: Cyan (low) to Blue (high)
            colors = np.zeros((points.shape[0], 4))
            colors[:, 0] = 0.0                      # Red
            colors[:, 1] = 0.5 + 0.5 * (1.0 - norm_z) # Green
            colors[:, 2] = 1.0                      # Blue
            colors[:, 3] = 0.7                      # Alpha
            
            self.scatter.setData(pos=points[:, :3], color=colors)
        except Exception as e:
            logger.debug(f"Error updating pointcloud scatter plot: {e}")

    def update_trajectory(self, path: list):
        """Updates the 3D line strip representing the robot's traversed trajectory."""
        if not self.initialized or not path:
            return
            
        try:
            pts = np.array(path, dtype=np.float32)
            if pts.ndim == 2 and pts.shape[1] == 2:
                # Add Z=0 coordinate
                pts_3d = np.zeros((pts.shape[0], 3), dtype=np.float32)
                pts_3d[:, :2] = pts
                self.trajectory_line.setData(pos=pts_3d)
        except Exception as e:
            logger.debug(f"Error updating trajectory line: {e}")

    def update_robot_pose(self, x: float, y: float, yaw_deg: float):
        """Updates the position and orientation of the robot representation model & frame axes."""
        if not self.initialized:
            return
            
        try:
            # Rotate first, then translate to place it at the correct (x, y)
            self.robot_box.resetTransform()
            self.robot_box.rotate(yaw_deg, 0, 0, 1)
            # Offset robot box slightly in Z to center the box height on the ground
            self.robot_box.translate(x, y, 0.125)
            
            self.axes.resetTransform()
            self.axes.rotate(yaw_deg, 0, 0, 1)
            self.axes.translate(x, y, 0.0)
        except Exception as e:
            logger.debug(f"Error updating robot pose transform: {e}")

    def update_map(self, grid_data: np.ndarray, resolution: float, origin_x: float, origin_y: float):
        """Updates the 2D occupancy grid image texture and translates/scales it in the 3D scene."""
        if not self.initialized or grid_data is None:
            return
            
        try:
            # grid_data is W x H array with values: -1 (unknown), 0 (free), 100 (occupied)
            w, h = grid_data.shape
            rgba = np.zeros((w, h, 4), dtype=np.uint8)
            
            # Color map details:
            # Unknown (-1) -> Dark semi-transparent slate
            rgba[grid_data < 0] = [18, 18, 22, 120]
            # Free (0) -> Clear transparent (revealing grid)
            rgba[grid_data == 0] = [12, 12, 14, 0]
            # Occupied (>0) -> Neon Cyan obstacle walls
            rgba[grid_data > 0] = [0, 180, 216, 255]
            
            # Set texture
            self.map_image.setData(rgba)
            
            # Apply resolution scaling and origin translation
            self.map_image.resetTransform()
            self.map_image.translate(origin_x, origin_y, -0.01) # SLAM plane just below grid
            self.map_image.scale(resolution, resolution, 1.0)
        except Exception as e:
            logger.debug(f"Error updating occupancy grid map: {e}")

    # Layer visibility controls
    def toggle_grid(self, visible: bool):
        if self.initialized:
            self.grid.setVisible(visible)

    def toggle_axes(self, visible: bool):
        if self.initialized:
            self.axes.setVisible(visible)

    def toggle_model(self, visible: bool):
        if self.initialized:
            self.robot_box.setVisible(visible)

    def toggle_scatter(self, visible: bool):
        if self.initialized:
            self.scatter.setVisible(visible)

    def toggle_trajectory(self, visible: bool):
        if self.initialized:
            self.trajectory_line.setVisible(visible)

    def toggle_map(self, visible: bool):
        if self.initialized:
            self.map_image.setVisible(visible)

    def reset_view(self):
        if self.initialized:
            self.gl_widget.opts['distance'] = 12
            self.gl_widget.opts['elevation'] = 30
            self.gl_widget.opts['azimuth'] = 45
            self.gl_widget.update()

