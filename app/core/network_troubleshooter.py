import socket
import subprocess
import platform
import psutil
import time
from typing import Dict, Any, List

class NetworkTroubleshooter:
    @staticmethod
    def ping_host(host: str, count: int = 3) -> Dict[str, Any]:
        """Pings a target host and returns latency, packet loss, and status."""
        is_windows = platform.system() == "Windows"
        cmd = ["ping", "-n" if is_windows else "-c", str(count), host]
        
        start_time = time.time()
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=is_windows).decode('utf-8', errors='ignore')
            elapsed = (time.time() - start_time) * 1000
            
            # Parse output
            loss = 100
            latency = -1.0
            
            if is_windows:
                # Look for "Lost = X (Y% loss)"
                for line in output.split("\n"):
                    if "loss" in line.lower() or "lost" in line.lower():
                        parts = line.split("(")
                        if len(parts) > 1:
                            loss_str = parts[1].split("%")[0].strip()
                            try:
                                loss = int(loss_str)
                            except ValueError:
                                pass
                    if "average" in line.lower() or "media" in line.lower():
                        parts = line.split("=")
                        if len(parts) > 1:
                            lat_str = parts[-1].replace("ms", "").strip()
                            try:
                                latency = float(lat_str)
                            except ValueError:
                                pass
            else:
                # Linux parsing
                for line in output.split("\n"):
                    if "packet loss" in line:
                        loss = int(line.split("%")[0].split()[-1])
                    if "rtt" in line or "min/avg/max" in line:
                        latency = float(line.split("=")[1].split("/")[1])
                        
            # Fallbacks
            if loss < 100 and latency < 0:
                latency = elapsed / count
                
            status = "green" if loss == 0 else ("yellow" if loss < 100 else "red")
            desc = f"Ping to {host} successful. Avg Latency: {latency:.1f}ms, Packet Loss: {loss}%." if loss < 100 else f"Failed to ping {host}. Destination unreachable."
            
            return {
                "success": loss < 100,
                "latency": latency,
                "packet_loss": loss,
                "status": status,
                "description": desc,
                "fix_suggestion": None if loss == 0 else ("Connect Go2 via Ethernet/WiFi directly." if loss == 100 else "Move closer to WiFi access point or replace cable.")
            }
        except subprocess.CalledProcessError:
            return {
                "success": False,
                "latency": -1.0,
                "packet_loss": 100,
                "status": "red",
                "description": f"Ping command failed. {host} is offline or blocking ICMP packets.",
                "fix_suggestion": "Verify robot is turned on, IP address is correct, and network cable is secure."
            }

    @staticmethod
    def test_port(host: str, port: int, timeout: float = 1.0) -> Dict[str, Any]:
        """Tries to connect to a target TCP port."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            s.close()
            return {
                "open": True,
                "status": "green",
                "description": f"Port {port} is open and listening.",
                "fix_suggestion": None
            }
        except Exception as e:
            return {
                "open": False,
                "status": "red",
                "description": f"Port {port} is closed or blocked: {e}.",
                "fix_suggestion": f"Check if service (e.g. SSH on port 22 or telemetry daemon on port {port}) is running on the robot."
            }

    @staticmethod
    def check_subnet_match(robot_ip: str) -> Dict[str, Any]:
        """Checks if the robot IP falls within the subnet of any local network interface."""
        try:
            r_parts = [int(x) for x in robot_ip.split(".")]
            if len(r_parts) != 4:
                return {"match": False, "status": "red", "description": "Invalid robot IP address.", "fix_suggestion": "Enter a valid IPv4 address."}
        except ValueError:
            return {"match": False, "status": "red", "description": "Invalid robot IP format.", "fix_suggestion": "Enter a valid IPv4 address."}

        adapters = psutil.net_if_addrs()
        for name, addrs in adapters.items():
            for addr in addrs:
                if addr.family == socket.AF_INET:  # IPv4
                    ip = addr.address
                    netmask = addr.netmask
                    if not netmask:
                        netmask = "255.255.255.0" # Default fallback
                    
                    try:
                        h_parts = [int(x) for x in ip.split(".")]
                        m_parts = [int(x) for x in netmask.split(".")]
                        
                        # Apply netmask
                        h_subnet = [h_parts[i] & m_parts[i] for i in range(4)]
                        r_subnet = [r_parts[i] & m_parts[i] for i in range(4)]
                        
                        if h_subnet == r_subnet and ip != "127.0.0.1":
                            return {
                                "match": True,
                                "status": "green",
                                "description": f"IP Match: Host is on subnet {'.'.join(str(x) for x in h_subnet)} via interface '{name}' ({ip}).",
                                "fix_suggestion": None
                            }
                    except Exception:
                        continue
                        
        return {
            "match": False,
            "status": "yellow",
            "description": f"Subnet mismatch: No local network interface matches the robot IP subnet ({'.'.join(robot_ip.split('.')[:3])}.X).",
            "fix_suggestion": "Change your Windows network adapter settings to static IP (e.g. 192.168.123.100, Netmask 255.255.255.0)."
        }

    @staticmethod
    def run_full_diagnostics(robot_ip: str) -> List[Dict[str, Any]]:
        """Aggregates all network tests for a specific robot IP."""
        diagnostics = []
        
        # 1. Subnet check
        diagnostics.append({
            "test": "Subnet Match Test",
            **NetworkTroubleshooter.check_subnet_match(robot_ip)
        })
        
        # 2. Ping check
        ping_res = NetworkTroubleshooter.ping_host(robot_ip)
        diagnostics.append({
            "test": f"Ping Check ({robot_ip})",
            "status": ping_res["status"],
            "description": ping_res["description"],
            "fix_suggestion": ping_res["fix_suggestion"]
        })
        
        # 3. SSH Port check
        ssh_res = NetworkTroubleshooter.test_port(robot_ip, 22)
        diagnostics.append({
            "test": "SSH Port Connection (Port 22)",
            "status": ssh_res["status"],
            "description": ssh_res["description"],
            "fix_suggestion": ssh_res["fix_suggestion"] if not ssh_res["open"] else "SSH service is reachable. Ready for authentication."
        })
        
        # 4. Telemetry Port Check
        zmq_res = NetworkTroubleshooter.test_port(robot_ip, 5555, timeout=0.5)
        diagnostics.append({
            "test": "ZeroMQ Telemetry (Port 5555)",
            "status": zmq_res["status"] if zmq_res["open"] else "yellow", # yellow warnings on telemetry port since it starts via SSH later
            "description": zmq_res["description"] if zmq_res["open"] else "Telemetry port is closed. The DASH bridge will launch it over SSH on connection.",
            "fix_suggestion": None if zmq_res["open"] else "Ensure the robot has python3-zmq installed."
        })

        return diagnostics
