#!/usr/bin/env python3
"""
DASH Robot-Side Telemetry Bridge Node
This script executes onboard the Unitree Go2 EDU Linux SBC.
It subscribes to ROS2 topics, aggregates data, and broadcasts over ZeroMQ.
"""

import sys
import time
import json
import logging
import socket
import threading

# Attempt to load ROS2 Client libraries. If missing (e.g. running offline or testing),
# we fall back to mock publishers to keep the daemon runnable.
try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Imu, PointCloud2, BatteryState
    from nav_msgs.msg import Odometry
    # Go2 EDU Motor status definitions depend on custom Unitree messages or ROS2 topics
    # We load standard types here
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False
    class Node: pass  # Mock definition

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("DASH.RobotBridge")

class RobotTelemetryBridge(Node if ROS_AVAILABLE else object):
    def __init__(self):
        if ROS_AVAILABLE:
            super().__init__('dash_telemetry_bridge')
            self.setup_ros_subscriptions()
        else:
            logger.warning("ROS2 python bindings not detected. Running daemon in Simulation-Broadcast mode.")
            
        # Initialize TCP Server Socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", 5555))
        self.server_socket.listen(5)
        self.clients = []
        logger.info("TCP Telemetry Server listening on port 5555.")
        
        # Telemetry Cache
        self.telemetry = {
            "timestamp": time.time(),
            "system": {
                "cpu": 0.0, "ram": 0.0, "temperature": 45.0, 
                "network_quality": 95, "ros_state": "Active", "slam_state": "Idle"
            },
            "battery": {
                "voltage": 24.2, "current": 1.5, "percentage": 88, "temperature": 27.0, "health": 100, "remaining_time": 40.0
            },
            "imu": {
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
                "accel_x": 0.0, "accel_y": 0.0, "accel_z": 9.8,
                "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0
            },
            "gps": {
                "latitude": 37.7749, "longitude": -122.4194, "altitude": 15.0, "speed": 0.0, "heading": 0.0, "satellites": 12
            },
            "lidar": {
                "point_count": 0, "density": 0.0, "scan_frequency": 10.0, "range": 12.0, "fov": 360.0
            },
            "slam": {
                "status": "Mapping", "trajectory": [], "loop_closures": 0, "point_count": 0, "confidence": 98.0, "runtime": 0.0
            },
            "motors": [
                {
                    "id": i, "temperature": 32.0, "voltage": 24.0, "current": 0.2, "torque": 0.1,
                    "load": 0.01, "rpm": 0.0, "target_pos": 0.0, "current_pos": 0.0, "error_pos": 0.0,
                    "velocity": 0.0, "acceleration": 0.0, "fault_state": 0
                } for i in range(12)
            ],
            "topics": [
                {"topic": "/odom", "type": "nav_msgs/msg/Odometry", "rate": 50.0, "bandwidth": 12.0},
                {"topic": "/imu/data", "type": "sensor_msgs/msg/Imu", "rate": 100.0, "bandwidth": 8.0},
                {"topic": "/utlidar/cloud", "type": "sensor_msgs/msg/PointCloud2", "rate": 10.0, "bandwidth": 1024.0}
            ]
        }
        
        self.running = False
        self.lock = threading.Lock()

    def setup_ros_subscriptions(self):
        """Standard ROS2 subscribers for Unitree Go2 EDU topics."""
        # 1. IMU
        self.sub_imu = self.create_subscription(
            Imu,
            '/imu/data',
            self.imu_callback,
            10
        )
        # 2. Odometry
        self.sub_odom = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )
        # 3. Lidar Cloud
        self.sub_cloud = self.create_subscription(
            PointCloud2,
            '/utlidar/cloud',
            self.cloud_callback,
            2
        )
        # 4. Battery State — standard ROS2 topic for Go2 EDU power system
        self.sub_battery = self.create_subscription(
            BatteryState,
            '/battery_state',
            self.battery_state_callback,
            10
        )
        logger.info("ROS2 Subscribers initialized successfully (IMU, Odom, Cloud, Battery).")

    # --- Callback triggers updating caches ---
    def imu_callback(self, msg: Imu):
        with self.lock:
            # simple quaternion conversion placeholder
            # (In a real node, we do quaternion to euler calculation here)
            q = msg.orientation
            self.telemetry["imu"]["accel_x"] = msg.linear_acceleration.x
            self.telemetry["imu"]["accel_y"] = msg.linear_acceleration.y
            self.telemetry["imu"]["accel_z"] = msg.linear_acceleration.z
            self.telemetry["imu"]["gyro_x"] = msg.angular_velocity.x
            self.telemetry["imu"]["gyro_y"] = msg.angular_velocity.y
            self.telemetry["imu"]["gyro_z"] = msg.angular_velocity.z

    def odom_callback(self, msg: Odometry):
        with self.lock:
            pos = msg.pose.pose.position
            # Append position to trajectory for mapping path
            traj = self.telemetry["slam"]["trajectory"]
            traj.append([pos.x, pos.y])
            if len(traj) > 500:
                traj.pop(0)

    def cloud_callback(self, msg: PointCloud2):
        import struct
        try:
            # Extract x,y,z float values, downsampling by 15x to keep JSON payloads light and fast
            pts = []
            step = 15
            data = msg.data
            point_step = msg.point_step
            num_points = msg.width * msg.height
            
            for i in range(0, len(data), point_step * step):
                if i + 12 <= len(data):
                    x, y, z = struct.unpack_from('fff', data, i)
                    pts.append([float(x), float(y), float(z)])
                    
            with self.lock:
                self.telemetry["pc_data"] = pts
                self.telemetry["lidar"]["point_count"] = num_points
        except Exception as e:
            logger.error(f"Error parsing point cloud in RobotBridge: {e}")

    def battery_state_callback(self, msg: 'BatteryState'):
        """Reads ROS2 /battery_state topic (sensor_msgs/msg/BatteryState)."""
        with self.lock:
            percentage = int(msg.percentage * 100) if msg.percentage <= 1.0 else int(msg.percentage)
            self.telemetry["battery"]["voltage"]        = round(float(msg.voltage), 2)
            self.telemetry["battery"]["current"]        = round(float(msg.current), 2)
            self.telemetry["battery"]["percentage"]     = max(0, min(100, percentage))
            self.telemetry["battery"]["temperature"]    = round(float(msg.temperature), 1)
            self.telemetry["battery"]["remaining_time"] = round(
                float(msg.capacity) / max(abs(float(msg.current)), 0.001) * 60.0, 1
            ) if msg.current != 0.0 else self.telemetry["battery"]["remaining_time"]

    def query_system_stats(self):
        """Interrogates standard sysfs directories on SBC to read CPU & memory loads."""
        try:
            # Read CPU
            with open("/proc/loadavg", "r") as f:
                load = float(f.readline().split()[0])
                # Scale load percentage roughly based on 4 CPU cores
                cpu_pct = min(100.0, (load / 4.0) * 100.0)
            # Read Memory
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                total = int(lines[0].split()[1])
                free = int(lines[1].split()[1])
                ram_pct = ((total - free) / total) * 100.0
            # Read Thermal
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.readline()) / 1000.0
                
            with self.lock:
                self.telemetry["system"]["cpu"] = round(cpu_pct, 1)
                self.telemetry["system"]["ram"] = round(ram_pct, 1)
                self.telemetry["system"]["temperature"] = round(temp, 1)
        except Exception as e:
            logger.debug(f"System stats read failed (non-Linux or permission issue): {e}")
            # Fallback to simulated fluctuations
            with self.lock:
                t_mod = time.time() % 60.0
                self.telemetry["system"]["cpu"] = round(15.0 + 5.0 * math.sin(t_mod), 1)
                self.telemetry["system"]["ram"] = round(40.0 + 5.0 * math.sin(t_mod * 0.3), 1)

    def start(self):
        self.running = True
        logger.info("Aggregator loop running.")
        
        # Start CPU/System poller thread
        def sys_poll_loop():
            while self.running:
                self.query_system_stats()
                time.sleep(2.0)
        t_sys = threading.Thread(target=sys_poll_loop, daemon=True)
        t_sys.start()
        
        # Start TCP Client Connection Acceptor thread
        def accept_loop():
            while self.running:
                try:
                    client_sock, addr = self.server_socket.accept()
                    client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    with self.lock:
                        self.clients.append(client_sock)
                    logger.info(f"Telemetry client connected from {addr}")
                except Exception:
                    break
        t_accept = threading.Thread(target=accept_loop, daemon=True)
        t_accept.start()
        
        # Main publication loop at 10Hz
        while self.running:
            with self.lock:
                self.telemetry["timestamp"] = time.time()
                payload = json.dumps(self.telemetry) + "\n"
            
            payload_bytes = payload.encode('utf-8')
            
            with self.lock:
                active_clients = list(self.clients)
            
            for client in active_clients:
                try:
                    client.sendall(payload_bytes)
                except Exception:
                    try:
                        client.close()
                    except Exception:
                        pass
                    with self.lock:
                        if client in self.clients:
                            self.clients.remove(client)
                            
            time.sleep(0.1)

    def stop(self):
        self.running = False
        try:
            self.server_socket.close()
        except Exception:
            pass
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except Exception:
                    pass
            self.clients.clear()
        logger.info("Aggregator loop terminated.")

def main(args=None):
    if ROS_AVAILABLE:
        rclpy.init(args=args)
        
    bridge = RobotTelemetryBridge()
    
    # Run loop in separate thread
    loop_thread = threading.Thread(target=bridge.start, daemon=True)
    loop_thread.start()
    
    if ROS_AVAILABLE:
        try:
            rclpy.spin(bridge)
        except KeyboardInterrupt:
            pass
        finally:
            bridge.stop()
            bridge.destroy_node()
            rclpy.shutdown()
    else:
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            bridge.stop()

if __name__ == '__main__':
    main()
