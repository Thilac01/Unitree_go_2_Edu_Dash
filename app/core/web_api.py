import threading
import time
import logging
from typing import List, Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from app.core.telemetry_bridge import telemetry_bridge

logger = logging.getLogger("DASH.APIServer")

app = FastAPI(
    title="DASH Robot SDK API",
    description="REST & WebSocket API center for Unitree Go2 EDU telemetry.",
    version="1.0.0"
)

# Active WebSocket connections
active_connections: List[WebSocket] = []
websocket_traffic_sent = 0
websocket_clients_total = 0

# --- REST API Endpoints ---
@app.get("/")
def read_root():
    return {
        "status": "online",
        "device": "Unitree Go2 EDU Control Station",
        "documentation": "/docs"
    }

@app.get("/api/telemetry")
def get_telemetry():
    """Returns the absolute full state of the robot telemetry."""
    return telemetry_bridge.latest_data

@app.get("/api/system")
def get_system():
    return telemetry_bridge.latest_data.get("system", {})

@app.get("/api/battery")
def get_battery():
    return telemetry_bridge.latest_data.get("battery", {})

@app.get("/api/imu")
def get_imu():
    return telemetry_bridge.latest_data.get("imu", {})

@app.get("/api/gps")
def get_gps():
    return telemetry_bridge.latest_data.get("gps", {})

@app.get("/api/lidar")
def get_lidar():
    return telemetry_bridge.latest_data.get("lidar", {})

@app.get("/api/motors")
def get_motors():
    return telemetry_bridge.latest_data.get("motors", [])

@app.get("/api/motor/{motor_id}")
def get_motor(motor_id: int):
    motors = telemetry_bridge.latest_data.get("motors", [])
    if 0 <= motor_id < len(motors):
        return motors[motor_id]
    raise HTTPException(status_code=404, detail="Motor ID out of range (0-11)")

# --- WebSocket Telemetry Loop ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global websocket_clients_total
    await websocket.accept()
    active_connections.append(websocket)
    websocket_clients_total += 1
    logger.info(f"WebSocket client connected from {websocket.client}")
    try:
        while True:
            # Send latest telemetry every 100ms
            data = telemetry_bridge.latest_data
            await websocket.send_json(data)
            global websocket_traffic_sent
            websocket_traffic_sent += len(str(data))
            await asyncio_sleep(0.1)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.error(f"WebSocket broadcast error: {e}")

async def asyncio_sleep(seconds: float):
    # Fallback to prevent import issues in FastAPI runtime context
    import asyncio
    await asyncio.sleep(seconds)

# --- Uvicorn Server Manager ---
class APIServerManager:
    def __init__(self):
        self.server: Optional[uvicorn.Server] = None
        self.thread: Optional[threading.Thread] = None
        self.port = 8000
        self.host = "0.0.0.0"
        self.is_running = False

    def start(self, host: str = "0.0.0.0", port: int = 8000):
        if self.is_running:
            return
            
        self.host = host
        self.port = port
        self.is_running = True
        
        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio"
        )
        self.server = uvicorn.Server(config)
        
        def run_srv():
            try:
                self.server.run()
            except Exception as e:
                logger.error(f"API Server failed to run: {e}")
            finally:
                self.is_running = False

        self.thread = threading.Thread(target=run_srv, daemon=True)
        self.thread.start()
        logger.info(f"FastAPI Server started on {host}:{port}")

    def stop(self):
        if not self.is_running or not self.server:
            return
            
        self.server.should_exit = True
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("FastAPI Server stopped.")

    def get_stats(self) -> dict:
        return {
            "active_connections": len(active_connections),
            "total_clients": websocket_clients_total,
            "bytes_sent": websocket_traffic_sent,
            "is_running": self.is_running,
            "port": self.port,
            "host": self.host
        }

    @staticmethod
    def generate_sdk_documentation(output_path: str):
        """Generates static HTML documentation explaining how to fetch robot data using the API."""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>DASH SDK Client Documentation</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1e1e24; color: #e2e8f0; margin: 40px; }
        h1 { color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
        h2 { color: #f28b25; margin-top: 30px; }
        code { background-color: #0d1117; color: #ff7b72; padding: 3px 6px; border-radius: 4px; font-family: Courier, monospace; }
        pre { background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d; overflow-x: auto; }
        .method { font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; margin-right: 10px; }
        .get { background-color: #2ea44f; color: white; }
        .ws { background-color: #8c40bf; color: white; }
        .endpoint { font-family: monospace; font-size: 1.1em; color: #a5d6ff; }
        .param { font-style: italic; color: #ff7b72; }
    </style>
</head>
<body>
    <h1>DASH SDK Client Documentation</h1>
    <p>Use the local REST and WebSocket server to interface with the Unitree Go2 EDU robot directly in custom Python, Javascript, C++, or Node scripts.</p>
    
    <h2>1. REST Telemetry Fetching</h2>
    <p>Read instantaneous snapshots of any sensor or joint value.</p>
    
    <div>
        <p><span class="method get">GET</span> <span class="endpoint">/api/telemetry</span></p>
        <p>Returns the entire nested telemetry structure (IMU, Battery, 12 Motors, GPS, SLAM states).</p>
    </div>
    
    <div>
        <p><span class="method get">GET</span> <span class="endpoint">/api/motor/<span class="param">motor_id</span></span></p>
        <p>Returns states for a specific motor (0 to 11). e.g., torque, velocity, temperature.</p>
    </div>

    <h2>2. Python Telemetry Code Example</h2>
    <pre>
import requests

ROBOT_API_URL = "http://localhost:8000/api/telemetry"

try:
    response = requests.get(ROBOT_API_URL)
    data = response.json()
    
    battery_level = data["battery"]["percentage"]
    roll = data["imu"]["roll"]
    front_right_hip_temp = data["motors"][0]["temperature"]
    
    print(f"Battery: {battery_level}%, Roll: {roll}°")
    print(f"FR Hip Temp: {front_right_hip_temp}°C")
except Exception as e:
    print(f"Error connecting to DASH API: {e}")
    </pre>

    <h2>3. Real-Time Telemetry over WebSocket</h2>
    <p>Stream live telemetry state updates at 10Hz.</p>
    <div>
        <p><span class="method ws">WS</span> <span class="endpoint">ws://localhost:8000/ws</span></p>
        <pre>
// JS Client Example
const socket = new WebSocket('ws://localhost:8000/ws');

socket.onmessage = function(event) {
    const telemetry = JSON.parse(event.data);
    console.log("Live Yaw:", telemetry.imu.yaw);
};
        </pre>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"SDK Documentation generated at {output_path}")

# Global API Server Manager
api_server = APIServerManager()
