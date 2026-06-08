import os
import threading
import logging
from PyQt5.QtCore import QObject, pyqtSignal
import paramiko

logger = logging.getLogger("DASH.SSHManager")

class SSHManager(QObject):
    connection_status = pyqtSignal(bool, str) # status, message
    shell_data_received = pyqtSignal(str)     # shell stdout stream
    transfer_progress = pyqtSignal(str, int, int) # filename, bytes_sent, total_bytes

    def __init__(self):
        super().__init__()
        self.client = None
        self.sftp = None
        self.shell_channel = None
        self.shell_thread = None
        self.host = None
        self.port = 22
        self.username = None
        self.password = None
        self.is_running_shell = False

    def connect(self, host: str, port: int = 22, username: str = "unitree", password: str = "123") -> bool:
        """Connects to remote SSH server in a background attempt."""
        self.disconnect()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=5.0
            )
            self.sftp = self.client.open_sftp()
            self.connection_status.emit(True, f"Connected to {host}:{port}")
            logger.info(f"SSH connected to {host}")
            return True
        except Exception as e:
            err_msg = str(e)
            logger.error(f"SSH connection failed: {err_msg}")
            self.connection_status.emit(False, f"Connection failed: {err_msg}")
            self.client = None
            self.sftp = None
            return False

    def disconnect(self):
        self.is_running_shell = False
        if self.shell_channel:
            try:
                self.shell_channel.close()
            except Exception:
                pass
            self.shell_channel = None
            
        if self.sftp:
            try:
                self.sftp.close()
            except Exception:
                pass
            self.sftp = None
            
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
            logger.info("SSH disconnected")
            
        self.connection_status.emit(False, "Disconnected")

    def is_connected(self) -> bool:
        return self.client is not None and self.client.get_transport() is not None and self.client.get_transport().is_active()

    def execute_command(self, command: str, timeout: float = 10.0) -> tuple[int, str, str]:
        """Executes a single command synchronously and returns (exit_status, stdout, stderr)."""
        if not self.is_connected():
            return -1, "", "Not connected to robot SSH."
            
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()
            out_str = stdout.read().decode('utf-8', errors='ignore')
            err_str = stderr.read().decode('utf-8', errors='ignore')
            return exit_status, out_str, err_str
        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {e}")
            return -1, "", str(e)

    # --- Interactive Shell Subsystem ---
    def start_interactive_shell(self):
        """Spawns a pseudo-terminal (pty) channel for interactive shell usage."""
        if not self.is_connected():
            return
            
        try:
            trans = self.client.get_transport()
            self.shell_channel = trans.open_session()
            self.shell_channel.get_pty(term='vt100', width=120, height=40)
            self.shell_channel.invoke_shell()
            self.is_running_shell = True
            
            # Start background reader thread
            self.shell_thread = threading.Thread(target=self._read_shell_loop, daemon=True)
            self.shell_thread.start()
            logger.info("Interactive SSH shell started.")
        except Exception as e:
            logger.error(f"Failed to start interactive shell: {e}")

    def write_to_shell(self, data: str):
        if self.shell_channel and self.is_running_shell:
            try:
                self.shell_channel.send(data)
            except Exception as e:
                logger.error(f"Shell send error: {e}")

    def _read_shell_loop(self):
        """Reads stdout from remote pty shell channel and emits it."""
        while self.is_running_shell:
            try:
                if self.shell_channel and self.shell_channel.recv_ready():
                    data = self.shell_channel.recv(1024).decode('utf-8', errors='ignore')
                    if not data:
                        break
                    self.shell_data_received.emit(data)
                else:
                    threading.Event().wait(0.02)
            except Exception as e:
                logger.debug(f"Shell read exception: {e}")
                break
                
        self.is_running_shell = False
        logger.info("Interactive SSH shell stopped.")

    # --- SFTP Operations ---
    def list_remote_dir(self, path: str = ".") -> list[dict]:
        """Lists directory contents on remote robot, returning standard metadata dicts."""
        if not self.is_connected() or not self.sftp:
            return []
            
        try:
            # Change directory to resolve absolute paths if relative
            self.sftp.chdir(path)
            current_path = self.sftp.getcwd()
            entries = self.sftp.listdir_attr(current_path)
            
            result = []
            for attr in entries:
                is_dir = (attr.st_mode & 0o170000) == 0o040000
                result.append({
                    "name": attr.filename,
                    "is_dir": is_dir,
                    "size": attr.st_size,
                    "mtime": attr.st_mtime,
                    "permissions": oct(attr.st_mode)[-4:]
                })
            # Sort: Directories first, then alphabetically
            result.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            return result
        except Exception as e:
            logger.error(f"Failed to list remote directory {path}: {e}")
            return []

    def upload_file(self, local_path: str, remote_path: str):
        """Uploads a file via SFTP in a background thread."""
        if not self.is_connected() or not self.sftp:
            return
            
        filename = os.path.basename(local_path)
        
        def _upload():
            try:
                def progress_cb(sent, total):
                    self.transfer_progress.emit(filename, sent, total)
                
                self.sftp.put(local_path, remote_path, callback=progress_cb)
                logger.info(f"Successfully uploaded {filename} to {remote_path}")
            except Exception as e:
                logger.error(f"SFTP upload failed for {filename}: {e}")
                
        threading.Thread(target=_upload, daemon=True).start()

    def download_file(self, remote_path: str, local_path: str):
        """Downloads a file via SFTP in a background thread."""
        if not self.is_connected() or not self.sftp:
            return
            
        filename = os.path.basename(remote_path)
        
        def _download():
            try:
                def progress_cb(recv, total):
                    self.transfer_progress.emit(filename, recv, total)
                
                self.sftp.get(remote_path, local_path, callback=progress_cb)
                logger.info(f"Successfully downloaded {filename} to {local_path}")
            except Exception as e:
                logger.error(f"SFTP download failed for {filename}: {e}")
                
        threading.Thread(target=_download, daemon=True).start()

# Global SSH Manager instance
ssh_manager = SSHManager()
