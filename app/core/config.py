import os
import json
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.path.expanduser("~")) / ".dash_robotics"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "dash.db"
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Default Robot Configurations
DEFAULT_ROBOT_IP = "192.168.123.161"  # Default Unitree Go2 SBC IP on LAN
DEFAULT_SSH_PORT = 22
DEFAULT_SSH_USER = "unitree"
DEFAULT_SSH_PASS = "123"

# Networking Configuration defaults
DEFAULT_ZMQ_PORT = 5555
DEFAULT_WS_PORT = 8765
DEFAULT_API_PORT = 8000
DEFAULT_ROS_DOMAIN_ID = 0

# App Settings Keys
THEME_KEY = "ui_theme"
DARK_THEME = "dark"
LIGHT_THEME = "light"

def get_db_path() -> str:
    return str(DB_PATH)

def get_log_dir() -> str:
    return str(LOG_DIR)
