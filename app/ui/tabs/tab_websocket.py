from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QGridLayout, QTextBrowser, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSlot
from app.core.web_api import api_server
import json

class TabWebSocket(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title
        self.layout.addWidget(QLabel("<h2>Local WebSocket Telemetry Broadcaster</h2>"))
        self.layout.addWidget(QLabel("<p style='color:#94a3b8;'>Broadcast aggregated robot telemetry streams to listening client applications in real-time at 10Hz.</p>"))
        
        # Horizontal Split
        self.split_layout = QHBoxLayout()
        self.layout.addLayout(self.split_layout)
        
        # Left Panel - Status & Actions
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Actions Group
        self.actions_group = QGroupBox("Server Controls")
        self.actions_grid = QGridLayout(self.actions_group)
        
        self.btn_start = QPushButton("Start API Server")
        self.btn_start.setObjectName("btn_connect") # Cyan accent
        self.btn_start.clicked.connect(self.start_server)
        self.actions_grid.addWidget(self.btn_start, 0, 0)
        
        self.btn_stop = QPushButton("Stop API Server")
        self.btn_stop.setStyleSheet("background-color: #e63946; color: white;")
        self.btn_stop.clicked.connect(self.stop_server)
        self.actions_grid.addWidget(self.btn_stop, 0, 1)
        self.left_layout.addWidget(self.actions_group)
        
        # Stats Group
        self.stats_group = QGroupBox("Server Traffic Statistics")
        self.stats_grid = QGridLayout(self.stats_group)
        
        self.lbl_status = QLabel("Server Status: OFFLINE")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #e63946;")
        self.stats_grid.addWidget(self.lbl_status, 0, 0, 1, 2)
        
        self.lbl_addr = QLabel("Address: 0.0.0.0:8000")
        self.stats_grid.addWidget(self.lbl_addr, 1, 0)
        
        self.lbl_clients = QLabel("Active Clients: 0")
        self.stats_grid.addWidget(self.lbl_clients, 1, 1)
        
        self.lbl_total_clients = QLabel("Total Connections: 0")
        self.stats_grid.addWidget(self.lbl_total_clients, 2, 0)
        
        self.lbl_traffic = QLabel("Traffic Sent: 0.00 KB")
        self.stats_grid.addWidget(self.lbl_traffic, 2, 1)
        
        self.left_layout.addWidget(self.stats_group)
        self.split_layout.addWidget(self.left_panel)
        
        # Right Panel - Live Message Inspector
        self.inspect_group = QGroupBox("WebSocket Message Broadcast Inspector")
        self.inspect_layout = QVBoxLayout(self.inspect_group)
        self.console = QTextBrowser()
        self.console.append("Server offline. Messages are logged here once a connection becomes active.")
        self.inspect_layout.addWidget(self.console)
        self.split_layout.addWidget(self.inspect_group)
        
        # Query timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_stats)
        self.timer.start(1000)

        # By default start the API server on app launch
        self.start_server()

    def start_server(self):
        if not api_server.is_running:
            api_server.start(host="0.0.0.0", port=8000)
            self.poll_stats()

    def stop_server(self):
        if api_server.is_running:
            api_server.stop()
            self.poll_stats()

    def poll_stats(self):
        stats = api_server.get_stats()
        
        if stats["is_running"]:
            self.lbl_status.setText("Server Status: ONLINE")
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #00d2ff;")
            self.lbl_addr.setText(f"Address: {stats['host']}:{stats['port']}")
            self.lbl_clients.setText(f"Active Clients: {stats['active_connections']}")
            self.lbl_total_clients.setText(f"Total Connections: {stats['total_clients']}")
            
            kb_sent = stats["bytes_sent"] / 1024.0
            if kb_sent > 1024:
                self.lbl_traffic.setText(f"Traffic Sent: {kb_sent/1024.0:.2f} MB")
            else:
                self.lbl_traffic.setText(f"Traffic Sent: {kb_sent:.2f} KB")
                
            # Print mock feed to inspector if clients are listening
            if stats["active_connections"] > 0:
                from app.core.telemetry_bridge import telemetry_bridge
                data_subset = {
                    "timestamp": telemetry_bridge.latest_data.get("timestamp"),
                    "yaw": telemetry_bridge.latest_data.get("imu", {}).get("yaw"),
                    "voltage": telemetry_bridge.latest_data.get("battery", {}).get("voltage"),
                    "cpu": telemetry_bridge.latest_data.get("system", {}).get("cpu")
                }
                # Log to text browser
                self.console.append(f"SENT >> {json.dumps(data_subset)}")
                scrollbar = self.console.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        else:
            self.lbl_status.setText("Server Status: OFFLINE")
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #e63946;")
            self.lbl_clients.setText("Active Clients: 0")
            self.lbl_traffic.setText("Traffic Sent: 0.00 KB")
