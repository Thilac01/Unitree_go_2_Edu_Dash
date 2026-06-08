import sys
import os
import time
import logging
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from app.core.config import get_log_dir
from app.core.database import db
from app.ui.styles import QSS_DARK_STYLE
from app.main_window import MainWindow

# Ensure directories exist
log_dir = get_log_dir()

# Set up logging configuration to output to both console and data directory file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] (%(name)s) %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(log_dir, "dash_app.log"), encoding='utf-8')
    ]
)

logger = logging.getLogger("DASH.Main")

def main():
    logger.info("Starting DASH Ground Control Station...")
    
    # Enable High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    
    # Initialize PyQt application
    app = QApplication(sys.argv)
    
    # Apply stylesheet
    app.setStyleSheet(QSS_DARK_STYLE)
    
    # 1. Setup & Display Splash Screen
    base_dir = os.path.dirname(os.path.abspath(__file__))
    splash_path = os.path.join(base_dir, "app", "ui", "splash.png")
    pixmap = QPixmap(splash_path)
    
    if pixmap.isNull():
        # Fallback dark background if splash image is not found
        from PyQt5.QtGui import QColor
        pixmap = QPixmap(800, 450)
        pixmap.fill(QColor("#121214"))
        
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    
    # Apply a modern font style for splash messages
    splash.setFont(app.font())
    splash.show()
    
    def update_loading_state(message: str, percentage: int, delay: float = 0.05):
        logger.info(f"Loading: {message} ({percentage}%)")
        styled_msg = f"  {message} ... {percentage}%"
        splash.showMessage(
            styled_msg, 
            Qt.AlignBottom | Qt.AlignLeft, 
            Qt.cyan
        )
        app.processEvents()
        if delay > 0:
            time.sleep(delay)
        
    update_loading_state("Initializing Database connection pool", 5)
    profiles = db.get_profiles()
    active_profile_str = ""
    for p in profiles:
        if p.get("is_active") == 1:
            active_profile_str = f" ({p['profile_name']} @ {p['ip_address']})"
            break
            
    update_loading_state(f"Database loaded successfully{active_profile_str}", 15)
    
    # Run preflight environment checks dynamically and display real system values!
    from app.core.preflight_check import PreflightChecker
    checks = [
        PreflightChecker.check_os,
        PreflightChecker.check_python,
        PreflightChecker.check_cpu_ram,
        PreflightChecker.check_disk_space,
        PreflightChecker.check_wsl,
        PreflightChecker.check_firewall,
        PreflightChecker.check_network_adapters,
        PreflightChecker.check_time_sync,
        PreflightChecker.check_usb_devices
    ]
    
    for idx, check_func in enumerate(checks):
        # Query real system stats dynamically
        result = check_func()
        progress = 20 + int((idx / len(checks)) * 65) # Scale from 20% to 85%
        message = f"Check {result['name']}: {result['desc']}"
        update_loading_state(message, progress, delay=0.15) # 150ms delay to make it readable
        
    update_loading_state("Loading interface layouts and styling systems", 90)
    # Initialize main UI window
    window = MainWindow()
    
    update_loading_state("Launching DASH Ground Control Station", 100, delay=0.1)
    
    window.show()
    splash.finish(window)
    
    logger.info("Application loop running.")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
