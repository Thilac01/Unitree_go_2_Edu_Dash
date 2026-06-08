import sqlite3
import logging
from typing import List, Dict, Any, Optional
from app.core.config import get_db_path

logger = logging.getLogger("DASH.Database")

class DatabaseManager:
    def __init__(self):
        self.db_path = get_db_path()
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Creates the initial database schema if it does not exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 1. Settings Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                # 2. Command History Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS command_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        command TEXT NOT NULL
                    )
                """)
                # 3. Saved Command Shortcuts
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS saved_commands (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        command TEXT NOT NULL,
                        description TEXT
                    )
                """)
                # 4. Connection Profiles
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS connection_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        profile_name TEXT UNIQUE,
                        ip_address TEXT NOT NULL,
                        ssh_port INTEGER DEFAULT 22,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        ros_domain_id INTEGER DEFAULT 0,
                        is_active INTEGER DEFAULT 0
                    )
                """)
                
                # Insert default connection profile if empty
                cursor.execute("SELECT COUNT(*) as count FROM connection_profiles")
                if cursor.fetchone()["count"] == 0:
                    cursor.execute("""
                        INSERT INTO connection_profiles (profile_name, ip_address, ssh_port, username, password, ros_domain_id, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ("Default Go2", "192.168.123.161", 22, "unitree", "123", 0, 1))

                # Insert some default saved commands if empty
                cursor.execute("SELECT COUNT(*) as count FROM saved_commands")
                if cursor.fetchone()["count"] == 0:
                    default_cmds = [
                        ("Start ROS", "source /opt/ros/foxy/setup.bash && ros2 launch unitree_lidar_sdk launch.py", "Launches Lidar SDK & ROS nodes"),
                        ("Stop ROS", "pkill -f ros2", "Kills all active ROS2 processes"),
                        ("Start SLAM", "cd /home/unitree/SLAM && ./start_slam.sh", "Starts standard 3D mapping SLAM"),
                        ("Check Hardware", "vcgencmd measure_temp || cat /sys/class/thermal/thermal_zone0/temp", "Check CPU Temperature on SBC"),
                        ("Reboot Robot", "sudo reboot", "Reboots Go2 motherboard computer"),
                    ]
                    cursor.executemany("""
                        INSERT INTO saved_commands (name, command, description)
                        VALUES (?, ?, ?)
                    """, default_cmds)

                conn.commit()
                logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)

    # --- Settings Handlers ---
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row["value"] if row else default
        except Exception as e:
            logger.error(f"Failed to read setting {key}: {e}")
            return default

    def set_setting(self, key: str, value: str):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """, (key, str(value)))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to set setting {key}={value}: {e}")

    # --- Connection Profiles Handlers ---
    def get_profiles(self) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM connection_profiles ORDER BY id DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to retrieve connection profiles: {e}")
            return []

    def get_active_profile(self) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM connection_profiles WHERE is_active = 1 LIMIT 1")
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get active profile: {e}")
            return None

    def set_active_profile(self, profile_id: int):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE connection_profiles SET is_active = 0")
                cursor.execute("UPDATE connection_profiles SET is_active = 1 WHERE id = ?", (profile_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to activate profile {profile_id}: {e}")

    def add_profile(self, name: str, ip: str, port: int, user: str, pswd: str, domain: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO connection_profiles (profile_name, ip_address, ssh_port, username, password, ros_domain_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, ip, port, user, pswd, domain))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add profile: {e}")
            return False

    def delete_profile(self, profile_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM connection_profiles WHERE id = ?", (profile_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete profile: {e}")
            return False

    # --- Command History Handlers ---
    def add_command_history(self, command: str):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO command_history (command) VALUES (?)", (command,))
                # Cap history at 500 entries
                cursor.execute("""
                    DELETE FROM command_history WHERE id NOT IN (
                        SELECT id FROM command_history ORDER BY id DESC LIMIT 500
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log command history: {e}")

    def get_command_history(self) -> List[str]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT command FROM command_history ORDER BY id DESC")
                return [row["command"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get command history: {e}")
            return []

    # --- Saved Commands Handlers ---
    def get_saved_commands(self) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM saved_commands")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get saved commands: {e}")
            return []

    def add_saved_command(self, name: str, command: str, description: str = "") -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO saved_commands (name, command, description)
                    VALUES (?, ?, ?)
                """, (name, command, description))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add saved command: {e}")
            return False

    def delete_saved_command(self, cmd_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM saved_commands WHERE id = ?", (cmd_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete saved command: {e}")
            return False

# Global database instance
db = DatabaseManager()
