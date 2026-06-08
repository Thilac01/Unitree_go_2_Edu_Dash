import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
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
                self.axes.setSize(3, 3, 3)
                self.gl_widget.addItem(self.axes)
                
                # Scatter plot item for the Lidar point cloud
                self.scatter = gl.GLScatterPlotItem(
                    pos=np.zeros((1, 3)), 
                    color=(0.0, 0.7, 1.0, 0.8), 
                    size=2.5, 
                    pxMode=True
                )
                self.gl_widget.addItem(self.scatter)
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
        lbl.setAlignment(Qt.AlignCenter if 'Qt' in globals() else None) # simple fallback
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

    def reset_view(self):
        if self.initialized:
            self.gl_widget.opts['distance'] = 12
            self.gl_widget.opts['elevation'] = 30
            self.gl_widget.opts['azimuth'] = 45
            self.gl_widget.update()
