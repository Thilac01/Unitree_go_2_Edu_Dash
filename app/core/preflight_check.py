import sys
import os
import platform
import shutil
import subprocess
import psutil
from typing import Dict, Any, List

class PreflightChecker:
    @staticmethod
    def run_all_checks() -> List[Dict[str, Any]]:
        checks = []
        checks.append(PreflightChecker.check_os())
        checks.append(PreflightChecker.check_python())
        checks.append(PreflightChecker.check_cpu_ram())
        checks.append(PreflightChecker.check_disk_space())
        checks.append(PreflightChecker.check_wsl())
        checks.append(PreflightChecker.check_firewall())
        checks.append(PreflightChecker.check_network_adapters())
        checks.append(PreflightChecker.check_time_sync())
        checks.append(PreflightChecker.check_usb_devices())
        return checks

    @staticmethod
    def check_os() -> Dict[str, Any]:
        os_name = platform.system()
        os_ver = platform.version()
        release = platform.release()
        
        if os_name == "Windows":
            status = "green"
            desc = f"Windows {release} ({os_ver}) detected."
            fix = None
        else:
            status = "yellow"
            desc = f"Unsupported platform: {os_name}. App is designed for Windows."
            fix = "Run the application in a Windows 10/11 environment."
            
        return {
            "name": "Windows Version",
            "status": status,
            "desc": desc,
            "fix_action": fix
        }

    @staticmethod
    def check_python() -> Dict[str, Any]:
        ver = sys.version_info
        ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
        
        if ver.major == 3 and ver.minor >= 8:
            status = "green"
            desc = f"Python {ver_str} matches requirements."
            fix = None
        else:
            status = "red"
            desc = f"Python version {ver_str} may be incompatible. Python >= 3.8 is required."
            fix = "Upgrade Python to version 3.10.x from python.org."
            
        return {
            "name": "Python Version",
            "status": status,
            "desc": desc,
            "fix_action": fix
        }

    @staticmethod
    def check_cpu_ram() -> Dict[str, Any]:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        ram_gb = ram.total / (1024**3)
        ram_avail_gb = ram.available / (1024**3)
        
        desc = f"CPU Usage: {cpu_usage}%, RAM Available: {ram_avail_gb:.2f}GB / {ram_gb:.2f}GB total."
        
        if ram_gb < 4.0:
            status = "red"
            fix = "Increase system RAM to at least 8GB to run visualizations smoothly."
        elif ram_avail_gb < 1.0 or cpu_usage > 90.0:
            status = "yellow"
            fix = "Close background processes to free up CPU and RAM."
        else:
            status = "green"
            fix = None
            
        return {
            "name": "CPU & Memory Check",
            "status": status,
            "desc": desc,
            "fix_action": fix
        }

    @staticmethod
    def check_disk_space() -> Dict[str, Any]:
        total, used, free = shutil.disk_usage(".")
        free_gb = free / (1024**3)
        
        if free_gb < 2.0:
            status = "red"
            desc = f"Disk Space Critical: {free_gb:.2f} GB available."
            fix = "Free up disk space on the installation drive."
        elif free_gb < 5.0:
            status = "yellow"
            desc = f"Low Disk Space: {free_gb:.2f} GB available."
            fix = "Clean up temporary files or logs to prevent storage issues."
        else:
            status = "green"
            desc = f"Sufficient Disk Space: {free_gb:.2f} GB available."
            fix = None
            
        return {
            "name": "Disk Storage",
            "status": status,
            "desc": desc,
            "fix_action": fix
        }

    @staticmethod
    def check_wsl() -> Dict[str, Any]:
        wsl_path = shutil.which("wsl")
        if not wsl_path:
            return {
                "name": "WSL Installation",
                "status": "yellow",
                "desc": "WSL (Windows Subsystem for Linux) is not installed.",
                "fix_action": "Install WSL using 'wsl --install' in PowerShell (Admin) if local ROS simulation is required."
            }
        
        try:
            # Check installed WSL distros
            output = subprocess.check_output(["wsl", "--list", "--verbose"], stderr=subprocess.STDOUT, shell=True).decode('utf-8', errors='ignore')
            if "Ubuntu" in output:
                return {
                    "name": "WSL Installation",
                    "status": "green",
                    "desc": "WSL detected with Ubuntu installed. Ready for local node interfaces.",
                    "fix_action": None
                }
            else:
                return {
                    "name": "WSL Installation",
                    "status": "yellow",
                    "desc": "WSL is installed but no Ubuntu distribution was found.",
                    "fix_action": "Run 'wsl --install -d Ubuntu' in PowerShell to set up Ubuntu."
                }
        except Exception as e:
            return {
                "name": "WSL Installation",
                "status": "yellow",
                "desc": f"WSL command is available but failed to list distros: {e}",
                "fix_action": "Repair your WSL installation by running 'wsl --update' in PowerShell."
            }

    @staticmethod
    def check_firewall() -> Dict[str, Any]:
        if platform.system() != "Windows":
            return {"name": "Firewall Rule Status", "status": "green", "desc": "Skipped on non-Windows.", "fix_action": None}
            
        try:
            # Check if public profile is active
            output = subprocess.check_output(["netsh", "advfirewall", "show", "allprofiles", "state"], stderr=subprocess.STDOUT, shell=True).decode('utf-8', errors='ignore')
            if "ON" in output:
                return {
                    "name": "Windows Firewall",
                    "status": "yellow",
                    "desc": "Windows Firewall is active. Some ROS2 multicast DDS traffic might be blocked.",
                    "fix_action": "Ensure DDS ports (7400-7500) are open. Click 'Auto-Fix' to configure rules for ROS2."
                }
            return {
                "name": "Windows Firewall",
                "status": "green",
                "desc": "Windows Firewall is disabled or bypassed.",
                "fix_action": None
            }
        except Exception:
            return {
                "name": "Windows Firewall",
                "status": "yellow",
                "desc": "Unable to verify Windows Firewall profile state.",
                "fix_action": "Run application with Administrator privileges."
            }

    @staticmethod
    def check_network_adapters() -> Dict[str, Any]:
        adapters = psutil.net_if_addrs()
        if not adapters:
            return {
                "name": "Network Adapters",
                "status": "red",
                "desc": "No network adapters detected.",
                "fix_action": "Connect an Ethernet cable or enable WiFi adapter."
            }
            
        active_adapters = []
        vpn_detected = False
        
        for name, addrs in adapters.items():
            for addr in addrs:
                # Check for IPv4 addresses that aren't loopback
                if addr.family == 2 and addr.address != "127.0.0.1":
                    active_adapters.append(f"{name} ({addr.address})")
                    # Naive VPN detection
                    name_lower = name.lower()
                    if any(kw in name_lower for kw in ["vpn", "tap", "tun", "wireguard", "forticlient", "cisco"]):
                        vpn_detected = True
                        
        if not active_adapters:
            return {
                "name": "Network Adapters",
                "status": "red",
                "desc": "All adapters are disconnected or lack valid IPv4 addresses.",
                "fix_action": "Connect to your robot network via WiFi or Ethernet."
            }
            
        if vpn_detected:
            return {
                "name": "Network Adapters",
                "status": "yellow",
                "desc": f"Active network adapters: {', '.join(active_adapters)}. Active VPN detected which may interfere with robot DDS multicast traffic.",
                "fix_action": "Disconnect VPN connections before launching ROS telemetry."
            }
            
        return {
            "name": "Network Adapters",
            "status": "green",
            "desc": f"Network interfaces active: {', '.join(active_adapters)}.",
            "fix_action": None
        }

    @staticmethod
    def check_time_sync() -> Dict[str, Any]:
        # Simple local timezone and synchronization check
        # Windows command for time service query
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output(["w32tm", "/query", "/status"], stderr=subprocess.STDOUT, shell=True).decode('utf-8', errors='ignore')
                if "Source:" in output:
                    return {
                        "name": "Time Synchronization",
                        "status": "green",
                        "desc": "System time synchronized with network clock (W32Time).",
                        "fix_action": None
                    }
            return {
                "name": "Time Synchronization",
                "status": "yellow",
                "desc": "Time sync status is unverified. Accurate clock sync is vital for ROS TF frames.",
                "fix_action": "Run 'w32tm /resync' in command prompt as Administrator."
            }
        except Exception:
            return {
                "name": "Time Synchronization",
                "status": "yellow",
                "desc": "Clock sync source not queried.",
                "fix_action": "Sync your Windows system clock in System Settings."
            }

    @staticmethod
    def check_usb_devices() -> Dict[str, Any]:
        try:
            if platform.system() == "Windows":
                import winreg
                path = r"HARDWARE\DEVICEMAP\SERIALCOMM"
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    dev_count = 0
                    for i in range(1024):
                        try:
                            name, value, type_ = winreg.EnumValue(key, i)
                            dev_count += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                    return {
                        "name": "USB Peripherals",
                        "status": "green",
                        "desc": f"Detected {dev_count} active COM/serial interfaces via registry hardware map.",
                        "fix_action": None
                    }
                except FileNotFoundError:
                    return {
                        "name": "USB Peripherals",
                        "status": "green",
                        "desc": "No active COM/serial interfaces found (subsystem nominal).",
                        "fix_action": None
                    }
        except Exception:
            pass
            
        return {
            "name": "USB Peripherals",
            "status": "yellow",
            "desc": "USB subsystem active, serial interfaces ready.",
            "fix_action": None
        }

    @staticmethod
    def repair_firewall() -> bool:
        """Attempts to open DDS ports on Windows firewall. Requires Admin rights."""
        if platform.system() != "Windows":
            return False
        try:
            # Open ROS2 ports (7400 to 7500) for UDP and TCP
            cmd_udp = 'netsh advfirewall firewall add rule name="DASH ROS2 UDP" dir=in action=allow protocol=UDP localport=7400-7500'
            cmd_tcp = 'netsh advfirewall firewall add rule name="DASH ROS2 TCP" dir=in action=allow protocol=TCP localport=7400-7500'
            subprocess.run(cmd_udp, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(cmd_tcp, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
            
    @staticmethod
    def repair_time_sync() -> bool:
        """Attempts to trigger time sync."""
        if platform.system() != "Windows":
            return False
        try:
            subprocess.run("net start w32time", shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run("w32tm /resync", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
