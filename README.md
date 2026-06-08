# DASH // Unitree Go2 EDU Ground Control Station

DASH (Desktop Assistant & Robotics Shell) is a commercial-grade desktop ground control station built in Python using PyQt5, designed specifically for the Unitree Go2 EDU quadruped. It completely eliminates terminal command typing, ROS version conflicts, WSL networking hurdles, and firewall configurations by encapsulating all procedures inside a button-driven graphical dashboard.

---

## Key Features

1. **Pre-Flight Environment Check**: Probes Windows OS, Python, WSL, NTP time sync, and network interfaces for compliance. Includes auto-firewall rules configuration.
2. **Connection Wizard**: Auto-discovery and connection sequences (Ping, SSH authentication, SDK verification, ROS environment checks).
3. **Interactive SSH Console**: Full multi-tab monospace terminal emulation combined with a remote SFTP file explorer (drag/drop upload and downloads).
4. **3D Point Cloud View**: GPU-accelerated 3D OpenGL viewport displaying live rotating room scans from Lidar sensors using PyQtGraph.
5. **Computer Vision**: Live video streams from the front camera with real-time OpenCV-based AI object detection overlays.
6. **Sensor & Motor Dashboard**: Multi-axis IMU dials, battery cells analytics, and live graphs plotting currents and temperatures for all 12 motor joints.
7. **Control Center**: Standard virtual touchscreen joystick, WASD keyboard navigation, and native Windows XInput gamepad steering.
8. **FastAPI & WebSocket Server**: A local SDK layer broadcasting telemetry snapshots and live 10Hz socket streams for external scripting access.
9. **ROS Environment Manager**: One-click environment sourcing (Foxy, Humble, Iron) that automatically prefixes command executions.

---

## 📂 Folder Structure

```
DASH/
├── main.py                         # Application Entrypoint
├── requirements.txt                # Python Dependencies
├── app/
│   ├── main_window.py              # Main Window layout & view coordinator
│   ├── core/                       # Models & Core Logic (DB, SSH, ZMQ, Web Server)
│   │   ├── config.py               # Settings manager (JSON/SQLite paths)
│   │   ├── database.py             # SQLite database manager
│   │   ├── ssh_client.py           # SSH & SFTP connector
│   │   ├── telemetry_bridge.py     # ZMQ client / mock telemetry generator
│   │   ├── preflight_check.py      # Windows environment preflight check
│   │   ├── network_troubleshooter.py # Network diagnostic rules
│   │   └── gamepad.py              # Windows XInput gamepad controller
│   ├── ui/                         # Views & Custom Styles
│   │   ├── styles.py               # Custom dark-mode QSS stylesheet
│   │   ├── widgets/                # Reusable UI widgets (Terminal, Joystick, OpenGL 3D viewer)
│   │   └── tabs/                   # The 14 UI Page Tabs
│   └── robot_bridge/               # Onboard robot bridge script
│       └── dash_bridge.py          # Aggregator node to run on Go2 SBC
└── tests/                          # Automated Unit Tests
```

---

## ⚙️ Installation & Setup (Windows Host)

### 1. Prerequisites
- Install **Python 3.10.x** (Ensure you check "Add Python to PATH" during installation).
- A Windows 10 or 11 operating system.

### 2. Install Dependencies
Open PowerShell/CMD in the project folder and run:
```powershell
pip install -r requirements.txt
```

### 3. Run the Application
```powershell
python main.py
```
*Note: If testing offline, the application automatically boots into simulated telemetry mode (127.0.0.1) so you can test dials, graphs, joysticks, and 3D point clouds immediately.*

---

## 🤖 Deploying the Onboard Telemetry Bridge (Robot SBC)

To feed live data from the physical robot to your Windows DASH client, deploy the onboard aggregator node:

1. Connect your Windows PC to the Unitree Go2 network interface (WiFi or Ethernet).
2. Open the **Robot Connection Center** tab in DASH, insert credentials, and click **Connect**.
3. Go to the **Interactive Terminal** tab, use the SFTP browser to navigate to `/home/unitree`, and click **Upload File**. Select the bridge script:
   `app/robot_bridge/dash_bridge.py`.
4. Run the daemon on the robot SBC:
   ```bash
   chmod +x dash_bridge.py
   ./dash_bridge.py
   ```
5. Ensure ZeroMQ ports are open on the robot. The bridge will automatically stream ROS2 joint states and telemetry back to DASH on port 5555.

---

## 📦 PyInstaller Packaging (Single .exe Deployment)

To compile the application into a single portable Windows executable (.exe) that can be run on any PC without installing Python:

1. Install PyInstaller:
   ```powershell
   pip install pyinstaller
   ```
2. Build the application using the following optimized CLI command (combines resources, silences command prompts, and packages libraries):
   ```powershell
   pyinstaller --noconsole --onefile --name="DASH_Control_Center" --add-data "app;app" main.py
   ```
3. Once completed, find the standalone executable inside the `dist/` directory:
   `dist/DASH_Control_Center.exe`.
