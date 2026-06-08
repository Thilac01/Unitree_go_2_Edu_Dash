import json
import csv
import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel, QGroupBox, QFileDialog, QMessageBox, QHeaderView
from PyQt5.QtCore import Qt, pyqtSlot
from app.core.telemetry_bridge import telemetry_bridge
from app.core.database import db

class TabExplorer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title
        self.layout.addWidget(QLabel("<h2>ROS Topic Explorer</h2>"))
        self.layout.addWidget(QLabel("<p style='color:#94a3b8;'>Inspect active ROS2 channels on the robot. Monitor publication rates and record parameters to text or databases.</p>"))
        
        # Search and Filter
        self.filter_layout = QHBoxLayout()
        self.filter_layout.addWidget(QLabel("Filter:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by topic name or type...")
        self.search_input.textChanged.connect(self.apply_filter)
        self.filter_layout.addWidget(self.search_input)
        self.layout.addLayout(self.filter_layout)
        
        # Topic Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Topic Name", "Message Type", "Frequency (Hz)", "Bandwidth (KB/s)", "Msg Count"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.table)
        
        # Telemetry Logger Panel
        self.log_group = QGroupBox("Topic Recording Control")
        self.log_layout = QHBoxLayout(self.log_group)
        
        self.btn_record = QPushButton("Start Recording Topic Data")
        self.btn_record.clicked.connect(self.toggle_recording)
        self.log_layout.addWidget(self.btn_record)
        
        self.btn_csv = QPushButton("Export to CSV")
        self.btn_csv.clicked.connect(self.export_csv)
        self.log_layout.addWidget(self.btn_csv)
        
        self.btn_json = QPushButton("Export to JSON")
        self.btn_json.clicked.connect(self.export_json)
        self.log_layout.addWidget(self.btn_json)
        
        self.layout.addWidget(self.log_group)
        
        # Recording state
        self.is_recording = False
        self.recorded_data = []
        self.msg_counts = {}
        
        # Telemetry binding
        telemetry_bridge.telemetry_received.connect(self.on_telemetry)

    @pyqtSlot(dict)
    def on_telemetry(self, data: dict):
        topics = data.get("topics", [])
        search_txt = self.search_input.text().strip().lower()
        
        # Filter matching topics
        matched_topics = []
        for t in topics:
            tname = t["topic"].lower()
            ttype = t["type"].lower()
            if not search_txt or search_txt in tname or search_txt in ttype:
                matched_topics.append(t)
                
        self.table.setRowCount(len(matched_topics))
        
        for idx, t in enumerate(matched_topics):
            name = t["topic"]
            # Increment message count
            self.msg_counts[name] = self.msg_counts.get(name, 0) + int(t["rate"] * 0.1) # 100ms ticks
            
            # Name
            self.table.setItem(idx, 0, QTableWidgetItem(name))
            # Type
            self.table.setItem(idx, 1, QTableWidgetItem(t["type"]))
            # Rate
            self.table.setItem(idx, 2, QTableWidgetItem(f"{t['rate']:.1f}"))
            # Bandwidth
            self.table.setItem(idx, 3, QTableWidgetItem(f"{t['bandwidth']:.1f}"))
            # Count
            self.table.setItem(idx, 4, QTableWidgetItem(str(self.msg_counts[name])))
            
            # Record payload if active
            if self.is_recording:
                self.recorded_data.append({
                    "timestamp": time.time(),
                    "topic": name,
                    "type": t["type"],
                    "frequency": t["rate"],
                    "bandwidth": t["bandwidth"]
                })

    def apply_filter(self):
        # Triggered on text changes, list updates automatically on next telemetry tick
        pass

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recorded_data.clear()
            self.btn_record.setText("Stop Recording Topic Data")
            self.btn_record.setStyleSheet("background-color: #e63946; color: white;")
        else:
            self.is_recording = False
            self.btn_record.setText("Start Recording Topic Data")
            self.btn_record.setStyleSheet("")
            QMessageBox.information(self, "Recording Stopped", f"Recorded {len(self.recorded_data)} telemetry entries. Ready to export.")

    def export_csv(self):
        if not self.recorded_data:
            QMessageBox.warning(self, "No Data", "No logged data found. Please start topic recording first.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export to CSV", "topic_logs.csv", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Topic", "Type", "Frequency (Hz)", "Bandwidth (KB/s)"])
                    for row in self.recorded_data:
                        writer.writerow([row["timestamp"], row["topic"], row["type"], row["frequency"], row["bandwidth"]])
                QMessageBox.information(self, "Saved", "CSV exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save CSV: {e}")

    def export_json(self):
        if not self.recorded_data:
            QMessageBox.warning(self, "No Data", "No logged data found. Please start topic recording first.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export to JSON", "topic_logs.json", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.recorded_data, f, indent=4)
                QMessageBox.information(self, "Saved", "JSON exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save JSON: {e}")
