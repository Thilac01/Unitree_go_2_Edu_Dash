from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QRectF

class JoystickWidget(QWidget):
    # Emits x, y values between -1.0 and 1.0 (y is inverted so up is positive)
    joystick_moved = pyqtSignal(float, float)

    def __init__(self, parent=None, size=200):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.radius = size / 2
        self.center = QPoint(int(self.radius), int(self.radius))
        self.knob_pos = QPoint(int(self.radius), int(self.radius))
        self.knob_radius = size / 6
        self.boundary_radius = size * 0.4
        self.is_pressed = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw outer boundary circle
        painter.setPen(QPen(QColor("#00b4d8"), 2, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(30, 30, 36, 120)))
        painter.drawEllipse(self.center, int(self.boundary_radius), int(self.boundary_radius))

        # Draw inner guidelines (crosshairs)
        painter.setPen(QPen(QColor(45, 45, 52, 100), 1, Qt.DashLine))
        painter.drawLine(int(self.center.x() - self.boundary_radius), self.center.y(), int(self.center.x() + self.boundary_radius), self.center.y())
        painter.drawLine(self.center.x(), int(self.center.y() - self.boundary_radius), self.center.x(), int(self.center.y() + self.boundary_radius))

        # Draw current active knob position
        # Glowing gradient for the knob
        painter.setPen(Qt.NoPen)
        if self.is_pressed:
            painter.setBrush(QBrush(QColor("#00ffcc")))
        else:
            painter.setBrush(QBrush(QColor("#00b4d8")))
            
        painter.drawEllipse(self.knob_pos, int(self.knob_radius), int(self.knob_radius))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressed = True
            self.update_knob(event.pos())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_pressed:
            self.update_knob(event.pos())
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_pressed = False
        # Reset knob to center
        self.knob_pos = QPoint(self.center.x(), self.center.y())
        self.update()
        self.joystick_moved.emit(0.0, 0.0)
        event.accept()

    def update_knob(self, pos):
        dx = pos.x() - self.center.x()
        dy = pos.y() - self.center.y()
        distance = (dx**2 + dy**2)**0.5

        if distance <= self.boundary_radius:
            self.knob_pos = pos
        else:
            # Constrain to boundary circle
            angle_cos = dx / distance
            angle_sin = dy / distance
            self.knob_pos = QPoint(
                int(self.center.x() + self.boundary_radius * angle_cos),
                int(self.center.y() + self.boundary_radius * angle_sin)
            )

        self.update()

        # Normalize outputs (-1.0 to 1.0)
        norm_x = (self.knob_pos.x() - self.center.x()) / self.boundary_radius
        norm_y = -(self.knob_pos.y() - self.center.y()) / self.boundary_radius # Invert Y so up is +1.0
        self.joystick_moved.emit(round(norm_x, 3), round(norm_y, 3))
