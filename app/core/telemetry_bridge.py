import time
import json
import logging
import random
import math
from PyQt5.QtCore import QThread, pyqtSignal
import zmq
import numpy as np

logger = logging.getLogger("DASH.TelemetryBridge")

class TelemetryBridge(QThread):
    telemetry_received = pyqtSignal(dict)
    pointcloud_received = pyqtSignal(np.ndarray) # Nx3 float32 points

    def __init__(self):
        super().__init__()
        self.host = "127.0.0.1"
        self.port = 5555
        self.running = False
        self.simulated = True # Run in simulation by default for offline UI testing
        self.context = None
        self.socket = None
        self.latest_data = self.get_empty_telemetry()
        self.sim_tick = 0

    def set_connection(self, host: str, port: int = 5555, simulated: bool = False):
        self.host = host
        self.port = port
        self.simulated = simulated
        logger.info(f"Telemetry configured for {host}:{port} (Simulated: {simulated})")

    def stop(self):
        self.running = False
        self.wait()

    def get_empty_telemetry(self) -> dict:
        """Helper to return initial zero-filled structures."""
        return {
            "timestamp": time.time(),
            "system": {
                "cpu": 0.0,
                "ram": 0.0,
                "temperature": 0.0,
                "network_quality": 100,
                "ros_state": "Offline",
                "slam_state": "Idle"
            },
            "battery": {
                "voltage": 24.0,
                "current": 0.0,
                "percentage": 100,
                "temperature": 25.0,
                "health": 100,
                "remaining_time": 45.0
            },
            "imu": {
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
                "accel_x": 0.0, "accel_y": 0.0, "accel_z": 9.81,
                "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0
            },
            "gps": {
                "latitude": 37.7749, "longitude": -122.4194, "altitude": 10.0,
                "speed": 0.0, "heading": 0.0, "satellites": 0
            },
            "lidar": {
                "point_count": 0, "density": 0.0, "scan_frequency": 0.0, "range": 0.0, "fov": 360.0
            },
            "slam": {
                "status": "Idle", "trajectory": [], "loop_closures": 0, "point_count": 0, "confidence": 0.0, "runtime": 0.0
            },
            "motors": [
                {
                    "id": i, "temperature": 30.0, "voltage": 24.0, "current": 0.0, "torque": 0.0,
                    "load": 0.0, "rpm": 0.0, "target_pos": 0.0, "current_pos": 0.0, "error_pos": 0.0,
                    "velocity": 0.0, "acceleration": 0.0, "fault_state": 0
                } for i in range(12)
            ],
            "topics": []
        }

    def run(self):
        self.running = True
        logger.info("Telemetry bridge thread started.")
        
        # Initialize ZeroMQ context
        if not self.simulated:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.SUB)
            self.socket.setsockopt(zmq.CONFLATE, 1) # Keep only latest packet
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
            self.socket.connect(f"tcp://{self.host}:{self.port}")
            logger.info(f"Connected to ZMQ sub socket at tcp://{self.host}:{self.port}")

        while self.running:
            if self.simulated:
                # Generate high-fidelity simulated robot data at 10Hz
                data = self.generate_mock_telemetry()
                pc = self.generate_mock_pointcloud()
                self.latest_data = data
                self.telemetry_received.emit(data)
                self.pointcloud_received.emit(pc)
                time.sleep(0.1)
            else:
                # Listen to ZMQ port
                try:
                    # Non-blocking poll for incoming data
                    if self.socket.poll(timeout=100, flags=zmq.POLLIN):
                        msg = self.socket.recv_string()
                        data = json.loads(msg)
                        self.latest_data = data
                        self.telemetry_received.emit(data)
                        
                        # Check for point cloud array
                        if "pc_data" in data:
                            points = np.array(data["pc_data"], dtype=np.float32)
                            self.pointcloud_received.emit(points)
                    else:
                        time.sleep(0.01)
                except Exception as e:
                    logger.debug(f"Telemetry read error: {e}")
                    time.sleep(0.1)

        # Cleanup ZMQ
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.context:
            self.context.term()
            self.context = None
        logger.info("Telemetry bridge thread stopped.")

    def generate_mock_telemetry(self) -> dict:
        self.sim_tick += 1
        t = self.sim_tick * 0.1
        
        # Slow roll/pitch dynamics
        roll = 5.0 * math.sin(t * 0.5)
        pitch = 3.0 * math.cos(t * 0.3)
        yaw = (t * 2.0) % 360.0
        
        # System
        cpu = 15.0 + 10.0 * math.sin(t) + random.uniform(0, 3)
        ram = 42.5 + random.uniform(-0.1, 0.1)
        temp = 48.0 + 2.0 * math.sin(t * 0.05)
        net = max(60, int(95 + random.uniform(-5, 2)))
        
        # Battery discharging slowly
        bat_percentage = max(10, 85 - int(t / 120))
        bat_volt = 22.0 + (bat_percentage / 100.0) * 3.2
        bat_curr = 2.5 + 4.0 * abs(math.sin(t))
        bat_temp = 28.0 + 5.0 * (bat_curr / 6.5)

        # GPS walk
        lat = 37.7749 + 0.0001 * math.sin(t * 0.05)
        lon = -122.4194 + 0.0001 * math.cos(t * 0.05)

        # Motors: Hip roll, Hip pitch, Knee pitch for 4 legs (FR, FL, RR, RL)
        motors = []
        for i in range(12):
            leg_idx = i // 3
            joint_idx = i % 3
            
            # Simulate joint oscillation based on a walk cycle
            target = 0.5 * math.sin(t * 2.5 + leg_idx * math.pi/2) if joint_idx > 0 else 0.0
            current = target + random.uniform(-0.01, 0.01)
            rpm = 30.0 * math.cos(t * 2.5 + leg_idx * math.pi/2) if joint_idx > 0 else 0.0
            current_draw = abs(rpm) * 0.05 + 0.1
            torque = current_draw * 1.5
            
            motors.append({
                "id": i,
                "temperature": 35.0 + 5.0 * math.sin(t * 0.02) + (torque * 0.5),
                "voltage": bat_volt,
                "current": current_draw,
                "torque": torque,
                "load": torque / 15.0,
                "rpm": rpm,
                "target_pos": target,
                "current_pos": current,
                "error_pos": target - current,
                "velocity": rpm * 0.1047,
                "acceleration": 0.0,
                "fault_state": 0
            })

        # Topics
        topics = [
            {"topic": "/odom", "type": "nav_msgs/msg/Odometry", "rate": 50.0, "bandwidth": 12.5},
            {"topic": "/imu/data", "type": "sensor_msgs/msg/Imu", "rate": 100.0, "bandwidth": 8.2},
            {"topic": "/utlidar/cloud", "type": "sensor_msgs/msg/PointCloud2", "rate": 10.0, "bandwidth": 1024.5},
            {"topic": "/camera/image_raw", "type": "sensor_msgs/msg/Image", "rate": 30.0, "bandwidth": 4096.0},
            {"topic": "/tf", "type": "tf2_msgs/msg/TFMessage", "rate": 150.0, "bandwidth": 45.1}
        ]

        # SLAM
        slam_states = ["Mapping", "Localizing"]
        slam_status = slam_states[(self.sim_tick // 200) % 2]
        
        return {
            "timestamp": time.time(),
            "system": {
                "cpu": cpu,
                "ram": ram,
                "temperature": temp,
                "network_quality": net,
                "ros_state": "Running (Active Foxy)",
                "slam_state": slam_status
            },
            "battery": {
                "voltage": bat_volt,
                "current": bat_curr,
                "percentage": bat_percentage,
                "temperature": bat_temp,
                "health": 98,
                "remaining_time": (bat_percentage / 100.0) * 50.0
            },
            "imu": {
                "roll": roll,
                "pitch": pitch,
                "yaw": yaw,
                "accel_x": 0.1 * math.sin(t),
                "accel_y": 0.15 * math.cos(t),
                "accel_z": 9.81 + 0.2 * math.sin(t),
                "gyro_x": 0.05 * math.cos(t),
                "gyro_y": 0.02 * math.sin(t),
                "gyro_z": 0.1
            },
            "gps": {
                "latitude": lat,
                "longitude": lon,
                "altitude": 12.5 + math.sin(t*0.1),
                "speed": 0.4 + 0.3 * math.sin(t*0.5),
                "heading": yaw,
                "satellites": 14
            },
            "lidar": {
                "point_count": 12000,
                "density": 45.2,
                "scan_frequency": 10.0,
                "range": 15.0 + 5.0 * math.sin(t*0.2),
                "fov": 360.0
            },
            "slam": {
                "status": slam_status,
                "trajectory": [[0.05 * x, 0.02 * math.sin(x)] for x in range(min(self.sim_tick, 500))],
                "loop_closures": self.sim_tick // 300,
                "point_count": self.sim_tick * 1500,
                "confidence": 92.5 + 5.0 * math.sin(t*0.1),
                "runtime": t
            },
            "motors": motors,
            "topics": topics
        }

    def generate_mock_pointcloud(self) -> np.ndarray:
        """Generates a dynamic spinning 3D room pointcloud for rendering."""
        t = self.sim_tick * 0.05
        points = []
        
        # We generate a cylinder representing room walls + floor + ceiling
        # and rotate them over time to simulate a spinning robot lidar scan
        num_points = 1500
        
        # Floor (circle points)
        for i in range(300):
            r = random.uniform(0.1, 5.0)
            theta = random.uniform(0, 2*math.pi)
            points.append([r * math.cos(theta), r * math.sin(theta), -1.0])
            
        # Ceiling
        for i in range(200):
            r = random.uniform(0.1, 5.0)
            theta = random.uniform(0, 2*math.pi)
            points.append([r * math.cos(theta), r * math.sin(theta), 1.5])
            
        # Walls (cylinder outline)
        for i in range(800):
            h = random.uniform(-1.0, 1.5)
            theta = random.uniform(0, 2*math.pi)
            # Add some room features (columns)
            r = 4.0 if (theta < math.pi/4 or theta > 3*math.pi/4) else 5.0
            points.append([r * math.cos(theta), r * math.sin(theta), h])
            
        # An obstacle (a box)
        for i in range(200):
            x = random.uniform(1.0, 1.8)
            y = random.uniform(-1.0, -0.2)
            z = random.uniform(-1.0, 0.2)
            points.append([x, y, z])
            
        pts_np = np.array(points, dtype=np.float32)
        
        # Rotate around Z axis by t
        rot_matrix = np.array([
            [math.cos(t), -math.sin(t), 0],
            [math.sin(t),  math.cos(t), 0],
            [0,            0,           1]
        ], dtype=np.float32)
        
        rotated_xyz = pts_np @ rot_matrix.T
        
        N = rotated_xyz.shape[0]
        times = np.linspace(0.0, 0.1, N, dtype=np.float32)
        
        dists = np.linalg.norm(rotated_xyz, axis=1)
        densities = 50.0 / (dists + 0.2) + np.random.uniform(0, 5, N).astype(np.float32)
        
        pts_5d = np.zeros((N, 5), dtype=np.float32)
        pts_5d[:, :3] = rotated_xyz
        pts_5d[:, 3] = times
        pts_5d[:, 4] = densities
        
        return pts_5d

# Global telemetry bridge instance
telemetry_bridge = TelemetryBridge()
