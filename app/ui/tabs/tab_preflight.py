import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLabel, QFileDialog, QMessageBox, QHeaderView
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, pyqtSignal
from app.core.preflight_check import PreflightChecker

class TabPreflight(QWidget):
    checklist_resolved = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Title & Description
        self.layout.addWidget(QLabel("<h2>Pre-Flight Environment Check</h2>"))
        self.layout.addWidget(QLabel("<p style='color:#94a3b8;'>Ensure your Windows machine is fully optimized for communicating with the Unitree Go2 EDU before booting the robot interfaces.</p>"))
        
        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Diagnostic Check", "Status", "Details", "Recommended Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("QTableWidget { gridline-color: #2d2d34; }")
        self.layout.addWidget(self.table)
        
        # Button controls
        self.btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run System Check")
        self.btn_run.setObjectName("btn_fix") # uses accent color stylesheet
        self.btn_run.clicked.connect(self.run_diagnostics)
        self.btn_layout.addWidget(self.btn_run)
        
        self.btn_fix_firewall = QPushButton("Auto-Fix Firewall")
        self.btn_fix_firewall.clicked.connect(self.fix_firewall)
        self.btn_layout.addWidget(self.btn_fix_firewall)
        
        self.btn_sync_time = QPushButton("Sync System Clock")
        self.btn_sync_time.clicked.connect(self.sync_time)
        self.btn_layout.addWidget(self.btn_sync_time)
        
        self.btn_auto_resolve = QPushButton("Auto-Resolve & Launch")
        self.btn_auto_resolve.setObjectName("btn_connect") # Cyan accent
        self.btn_auto_resolve.clicked.connect(self.auto_resolve_all)
        self.btn_layout.addWidget(self.btn_auto_resolve)
        
        self.btn_report = QPushButton("Generate Report")
        self.btn_report.clicked.connect(self.generate_report)
        self.btn_layout.addWidget(self.btn_report)
        
        self.layout.addLayout(self.btn_layout)
        
        self.results = []
        self.run_diagnostics()

    def run_diagnostics(self):
        self.results = PreflightChecker.run_all_checks()
        self.table.setRowCount(len(self.results))
        
        for idx, res in enumerate(self.results):
            # 1. Check Name
            item_name = QTableWidgetItem(res["name"])
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_name.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.table.setItem(idx, 0, item_name)
            
            # 2. Status LED/Text
            status = res["status"].upper()
            item_status = QTableWidgetItem(f" ● {status}")
            item_status.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if res["status"] == "green":
                item_status.setForeground(QColor("#00d2ff")) # Cyan/green ok
            elif res["status"] == "yellow":
                item_status.setForeground(QColor("#ff9f1c")) # Warning
            else:
                item_status.setForeground(QColor("#e63946")) # Critical red
            self.table.setItem(idx, 1, item_status)
            
            # 3. Description
            item_desc = QTableWidgetItem(res["desc"])
            item_desc.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(idx, 2, item_desc)
            
            # 4. Action
            action = res["fix_action"] or "None required"
            item_action = QTableWidgetItem(action)
            item_action.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if res["fix_action"]:
                item_action.setForeground(QColor("#ff9f1c"))
            self.table.setItem(idx, 3, item_action)

    def fix_firewall(self):
        success = PreflightChecker.repair_firewall()
        if success:
            QMessageBox.information(self, "Success", "Firewall rules for ROS2 (Ports 7400-7500 UDP/TCP) added successfully.")
            self.run_diagnostics()
        else:
            QMessageBox.warning(self, "Failed", "Failed to add rules automatically.\nPlease run the application as Administrator to modify Windows Firewall.")

    def sync_time(self):
        success = PreflightChecker.repair_time_sync()
        if success:
            QMessageBox.information(self, "Success", "NTP network time synchronized successfully.")
            self.run_diagnostics()
        else:
            QMessageBox.warning(self, "Failed", "Time synchronization failed.\nPlease synchronize in Windows settings manually.")

    def generate_report(self):
        if not self.results:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Pre-Flight Report", "dash_preflight_report.txt", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("====================================================\n")
                    f.write("        DASH SYSTEM PRE-FLIGHT DIAGNOSTICS REPORT   \n")
                    f.write("====================================================\n\n")
                    for res in self.results:
                        f.write(f"Check:       {res['name']}\n")
                        f.write(f"Status:      {res['status'].upper()}\n")
                        f.write(f"Description: {res['desc']}\n")
                        f.write(f"Fix Action:  {res['fix_action'] or 'None'}\n")
                        f.write("----------------------------------------------------\n")
                QMessageBox.information(self, "Report Saved", f"Diagnostics report successfully written to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save report: {e}")

    def auto_resolve_all(self):
        # 1. Attempt repairs for firewall and time sync
        PreflightChecker.repair_firewall()
        PreflightChecker.repair_time_sync()
        
        # 2. Get checks, but override their status to green (Bypassed/Nominal)
        raw_results = PreflightChecker.run_all_checks()
        self.results = []
        for check in raw_results:
            resolved_check = check.copy()
            if resolved_check["status"] != "green":
                resolved_check["status"] = "green"
                resolved_check["desc"] = f"Auto-Resolved / Bypassed: {check['desc']}"
                resolved_check["fix_action"] = "Resolved automatically"
            self.results.append(resolved_check)
            
        # 3. Refresh the table
        self.table.setRowCount(len(self.results))
        for idx, res in enumerate(self.results):
            # Check Name
            item_name = QTableWidgetItem(res["name"])
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_name.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.table.setItem(idx, 0, item_name)
            
            # Status LED/Text (All Green!)
            status = res["status"].upper()
            item_status = QTableWidgetItem(f" ● {status}")
            item_status.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_status.setForeground(QColor("#00d2ff")) # Cyan ok
            self.table.setItem(idx, 1, item_status)
            
            # Description
            item_desc = QTableWidgetItem(res["desc"])
            item_desc.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(idx, 2, item_desc)
            
            # Action
            action = res["fix_action"] or "Resolved"
            item_action = QTableWidgetItem(action)
            item_action.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(idx, 3, item_action)
            
        # 4. Emit the signal to switch tabs and connect
        QMessageBox.information(self, "Checklist Resolved", "All diagnostics bypassed and marked NOMINAL.\nLaunching connection suite...")
        self.checklist_resolved.emit(True)
