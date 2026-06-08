import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextBrowser, QGroupBox, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from app.core.web_api import api_server

class TabAPI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title
        self.layout.addWidget(QLabel("<h2>DASH Client API & SDK Center</h2>"))
        self.layout.addWidget(QLabel("<p style='color:#94a3b8;'>Expose robot telemetry to external programming scripts on this PC or remote machines using HTTP REST requests.</p>"))
        
        # Details Group
        self.details_group = QGroupBox("Available Local Server REST Endpoints")
        self.details_layout = QVBoxLayout(self.details_group)
        
        endpoints = """
        <b>GET</b> <font color='#00d2ff'>http://localhost:8000/api/telemetry</font> - Retrieve the absolute nested telemetry tree (Motors, IMU, GPS, System).<br>
        <b>GET</b> <font color='#00d2ff'>http://localhost:8000/api/battery</font> - Retrieve state of charge percentage, voltage, and health.<br>
        <b>GET</b> <font color='#00d2ff'>http://localhost:8000/api/imu</font> - Retrieve Roll, Pitch, Yaw orientation angles.<br>
        <b>GET</b> <font color='#00d2ff'>http://localhost:8000/api/motors</font> - Retrieve torque, RPMs and temps for all 12 motor actuators.<br>
        <b>GET</b> <font color='#00d2ff'>http://localhost:8000/api/motor/{id}</font> - Retrieve properties for a single actuator joint (0-11).
        """
        lbl_endpoints = QLabel(endpoints)
        lbl_endpoints.setStyleSheet("line-height: 1.6em;")
        self.details_layout.addWidget(lbl_endpoints)
        self.layout.addWidget(self.details_group)
        
        # Code snippets
        self.code_group = QGroupBox("Client Python SDK Snippet Example")
        self.code_layout = QVBoxLayout(self.code_group)
        
        self.code_view = QTextBrowser()
        self.code_view.setStyleSheet("background-color: #0b0b0d; border: 1px solid #2d2d34;")
        
        snippet = """import requests

# Query local DASH REST service
DASH_API_URL = "http://localhost:8000/api/telemetry"

try:
    response = requests.get(DASH_API_URL)
    robot = response.json()
    
    print("Go2 Battery percentage:", robot["battery"]["percentage"], "%")
    print("IMU Yaw Orientation:   ", robot["imu"]["yaw"], "deg")
    print("FR Knee Motor torque:   ", robot["motors"][2]["torque"], "Nm")
except Exception as e:
    print("Failed to contact API server:", e)
"""
        self.code_view.setText(snippet)
        self.code_layout.addWidget(self.code_view)
        self.layout.addWidget(self.code_group)
        
        # Document Export Action
        self.btn_layout = QHBoxLayout()
        self.btn_doc = QPushButton("Export SDK Documentation Manual (HTML)")
        self.btn_doc.setObjectName("btn_save") # Uses accent styling
        self.btn_doc.clicked.connect(self.export_documentation)
        self.btn_layout.addWidget(self.btn_doc)
        self.layout.addLayout(self.btn_layout)

    def export_documentation(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save SDK Documentation", "dash_sdk_docs.html", "HTML Files (*.html)")
        if path:
            try:
                api_server.generate_sdk_documentation(path)
                QMessageBox.information(self, "Success", f"HTML SDK Documentation successfully written to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to write manual: {e}")
