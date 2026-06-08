from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QLabel
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor
import pyqtgraph as pg
from app.core.telemetry_bridge import telemetry_bridge

class TabMotor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title
        self.layout.addWidget(QLabel("<h2>Actuator & Motor Analytics</h2>"))
        
        # Splitter (Table on Left, Plots on Right)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.layout.addWidget(self.splitter)
        
        # Left Panel - Motor List Table
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 5, 0)
        
        self.table_group = QGroupBox("Joint Actuators Telemetry")
        self.table_layout = QVBoxLayout(self.table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Joint ID", "Temp (°C)", "Current (A)", "Torque (N·m)", "RPM", "Target Pos", "Current Pos"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self.motor_selection_changed)
        
        self.table_layout.addWidget(self.table)
        self.left_layout.addWidget(self.table_group)
        self.splitter.addWidget(self.left_panel)
        
        # Right Panel - Live Graph
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(5, 0, 0, 0)
        
        self.graph_group = QGroupBox("Joint Performance Analytics")
        self.graph_layout = QVBoxLayout(self.graph_group)
        
        self.lbl_selected = QLabel("<b>Selected Joint: Joint 0 (FR Hip Roll)</b>")
        self.graph_layout.addWidget(self.lbl_selected)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1a1a1e")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.addLegend()
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time Steps')
        
        self.curve_current = self.plot_widget.plot(pen=pg.mkPen('#ff3366', width=2), name="Current (A)")
        self.curve_temp = self.plot_widget.plot(pen=pg.mkPen('#ffc83b', width=2), name="Temperature (°C)")
        
        self.graph_layout.addWidget(self.plot_widget)
        self.right_layout.addWidget(self.graph_group)
        self.splitter.addWidget(self.right_panel)
        
        self.splitter.setSizes([600, 400])
        
        # Selected joint tracking
        self.selected_motor_id = 0
        self.max_pts = 100
        self.current_history = []
        self.temp_history = []
        
        # Joint name lookup
        self.joint_names = {
            0: "FR Hip Roll", 1: "FR Hip Pitch", 2: "FR Knee Pitch",
            3: "FL Hip Roll", 4: "FL Hip Pitch", 5: "FL Knee Pitch",
            6: "RR Hip Roll", 7: "RR Hip Pitch", 8: "RR Knee Pitch",
            9: "RL Hip Roll", 10: "RL Hip Pitch", 11: "RL Knee Pitch"
        }
        
        # Initialize table rows
        self.table.setRowCount(12)
        for i in range(12):
            self.table.setItem(i, 0, QTableWidgetItem(f"[{i}] {self.joint_names[i]}"))
            for col in range(1, 7):
                self.table.setItem(i, col, QTableWidgetItem("0.0"))
                
        # Select first row by default
        self.table.selectRow(0)
        
        # Bind telemetry
        telemetry_bridge.telemetry_received.connect(self.on_telemetry)

    def motor_selection_changed(self):
        selected_ranges = self.table.selectedRanges()
        if selected_ranges:
            row = selected_ranges[0].topRow()
            if row != self.selected_motor_id:
                self.selected_motor_id = row
                self.lbl_selected.setText(f"<b>Selected Joint: Joint {row} ({self.joint_names[row]})</b>")
                self.current_history.clear()
                self.temp_history.clear()

    @pyqtSlot(dict)
    def on_telemetry(self, data: dict):
        motors = data.get("motors", [])
        if len(motors) < 12:
            return
            
        for i in range(12):
            motor = motors[i]
            temp = motor.get("temperature", 30.0)
            curr = motor.get("current", 0.0)
            torque = motor.get("torque", 0.0)
            rpm = motor.get("rpm", 0.0)
            target = motor.get("target_pos", 0.0)
            pos = motor.get("current_pos", 0.0)
            
            # Update Table cell items
            # ID
            item_id = self.table.item(i, 0)
            if item_id:
                if motor.get("fault_state", 0) > 0:
                    item_id.setForeground(QColor("#e63946")) # Fault Red
                else:
                    item_id.setForeground(QColor("#ffffff"))
            
            # Temp column (highlight hot motors in red/yellow)
            item_temp = self.table.item(i, 1)
            if item_temp:
                item_temp.setText(f"{temp:.1f}")
                if temp > 65.0:
                    item_temp.setForeground(QColor("#e63946"))
                elif temp > 50.0:
                    item_temp.setForeground(QColor("#ff9f1c"))
                else:
                    item_temp.setForeground(QColor("#e2e8f0"))
                    
            # Current
            item_curr = self.table.item(i, 2)
            if item_curr:
                item_curr.setText(f"{curr:.2f}")
                
            # Torque
            item_torque = self.table.item(i, 3)
            if item_torque:
                item_torque.setText(f"{torque:.2f}")
                
            # RPM
            item_rpm = self.table.item(i, 4)
            if item_rpm:
                item_rpm.setText(f"{rpm:.1f}")
                
            # Target
            item_targ = self.table.item(i, 5)
            if item_targ:
                item_targ.setText(f"{target:.3f}")
                
            # Current Position
            item_pos = self.table.item(i, 6)
            if item_pos:
                item_pos.setText(f"{pos:.3f}")
                
        # Update active selected motor graphs
        sel_motor = motors[self.selected_motor_id]
        self.current_history.append(sel_motor.get("current", 0.0))
        self.temp_history.append(sel_motor.get("temperature", 30.0))
        
        if len(self.current_history) > self.max_pts:
            self.current_history.pop(0)
            self.temp_history.pop(0)
            
        self.curve_current.setData(self.current_history)
        self.curve_temp.setData(self.temp_history)
