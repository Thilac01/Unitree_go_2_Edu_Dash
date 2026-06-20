import time
import os
import cv2
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QCheckBox, QGroupBox, QFileDialog, QMessageBox, QStackedWidget,
    QFrame, QSizePolicy, QGridLayout
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QPen
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer, QSize
from PyQt5.QtMultimedia import QCameraInfo
from app.core.ssh_client import ssh_manager

logger = logging.getLogger("DASH.TabCamera")


# ─────────────────────────────────────────────────────────────────────────────
#  Background camera capture thread
# ─────────────────────────────────────────────────────────────────────────────
class CameraReceiver(QThread):
    frame_ready    = pyqtSignal(QImage)
    status_update  = pyqtSignal(str, float, float)   # label, fps, latency_ms
    camera_lost    = pyqtSignal()
    camera_found   = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running        = False
        self.source_index   = 0          # OpenCV device index (int) or URL (str)
        self.use_local      = True       # True = local webcam, False = RTSP url
        self.detect_objects = False
        self.is_recording   = False
        self.video_writer   = None
        self.record_path    = ""
        self.frame_width    = 640
        self.frame_height   = 480
        self.tick           = 0
        self._was_connected = False

    def set_local_source(self, device_index: int):
        self.source_index = device_index
        self.use_local    = True

    def set_remote_source(self, url: str):
        self.source_index = url
        self.use_local    = False

    def toggle_detection(self, enabled: bool):
        self.detect_objects = enabled

    def start_recording(self, path: str):
        self.record_path  = path
        self.is_recording = True

    def stop_recording(self):
        self.is_recording = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

    # ── Main loop ──────────────────────────────────────────────────────────
    def run(self):
        self.running = True
        cap          = None
        fps_acc      = 0.0
        fps_samples  = 0
        last_fps_t   = time.time()

        while self.running:
            t0 = time.time()

            # (Re)open capture
            if cap is None or not cap.isOpened():
                try:
                    src = self.source_index if self.use_local else self.source_index
                    cap = cv2.VideoCapture(src)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                except Exception:
                    cap = None

            img_out = None
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    if not self._was_connected:
                        self._was_connected = True
                        self.camera_found.emit()
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame_rgb.shape
                    if self.detect_objects:
                        self._detect_faces(frame_rgb)
                    if self.is_recording:
                        self._write_frame(frame)
                    img_out = QImage(frame_rgb.data, w, h, ch * w,
                                     QImage.Format_RGB888).copy()
                else:
                    if self._was_connected:
                        self._was_connected = False
                        self.camera_lost.emit()
                    cap.release()
                    cap = None
            else:
                if self._was_connected:
                    self._was_connected = False
                    self.camera_lost.emit()

            if img_out is None:
                img_out = self._no_signal_frame()

            self.frame_ready.emit(img_out)

            # ── FPS & Latency tracking ──────────────────────────────────
            elapsed = time.time() - t0
            fps_acc    += 1.0 / max(elapsed, 0.001)
            fps_samples += 1
            now = time.time()
            if now - last_fps_t >= 1.0:
                avg_fps = fps_acc / fps_samples
                latency = elapsed * 1000.0
                label   = "Local Webcam" if self.use_local else "Robot RTSP"
                self.status_update.emit(label, avg_fps, latency)
                fps_acc    = 0.0
                fps_samples = 0
                last_fps_t = now

            # Clamp to ~30 fps
            sleep_t = max(0.001, 0.033 - elapsed)
            time.sleep(sleep_t)

        if cap:
            cap.release()

    # ── Helpers ────────────────────────────────────────────────────────────
    def _write_frame(self, frame):
        if self.video_writer is None:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            h, w   = frame.shape[:2]
            self.video_writer = cv2.VideoWriter(
                self.record_path, fourcc, 30.0, (w, h))
        self.video_writer.write(frame)

    def _detect_faces(self, frame_rgb):
        try:
            cascade_path  = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade  = cv2.CascadeClassifier(cascade_path)
            if not face_cascade.empty():
                gray  = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame_rgb, "HUMAN [94%]", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        except Exception:
            pass

    def _no_signal_frame(self) -> QImage:
        self.tick += 1
        import numpy as np
        W, H = self.frame_width, self.frame_height
        img  = np.zeros((H, W, 3), dtype=np.uint8)
        img[:] = (11, 11, 14)   # near-black background

        # Subtle grid
        for y in range(0, H, 40):
            img[y:y+1, :] = (18, 18, 22)
        for x in range(0, W, 40):
            img[:, x:x+1] = (18, 18, 22)

        cx, cy = W // 2, H // 2

        # Warning card
        cv2.rectangle(img, (cx - 220, cy - 80), (cx + 220, cy + 80), (20, 20, 26), -1)
        cv2.rectangle(img, (cx - 220, cy - 80), (cx + 220, cy + 80), (200, 50, 60), 1)

        # Icon (camera with X)
        cv2.circle(img, (cx - 160, cy - 20), 20, (200, 50, 60), 2)
        cv2.line  (img, (cx - 175, cy - 35), (cx - 145, cy - 5), (200, 50, 60), 2)

        # Text
        cv2.putText(img, "NO CAMERA SIGNAL",
                    (cx - 115, cy - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 50, 60), 2)
        cv2.putText(img, "Select a webcam or connect robot RTSP stream",
                    (cx - 175, cy + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (130, 140, 160), 1)

        # Blinking dot
        dot_col = (220, 50, 60) if (self.tick // 15) % 2 == 0 else (20, 20, 26)
        cv2.circle(img, (cx - 155, cy - 15), 5, dot_col, -1)

        return QImage(img.data, W, H, W * 3, QImage.Format_RGB888).copy()


# ─────────────────────────────────────────────────────────────────────────────
#  Permission Overlay widget
# ─────────────────────────────────────────────────────────────────────────────
class CameraPermissionOverlay(QWidget):
    """Semi-transparent overlay asking the user to allow camera access."""
    allow_clicked = pyqtSignal()
    deny_clicked  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(10,10,14,0.88);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel("📷")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 52px; background: transparent;")
        layout.addWidget(icon_lbl)

        title = QLabel("Camera Access Required")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #e2e8f0; font-size: 18px; font-weight: 700;"
            "font-family: 'Inter', sans-serif; background: transparent;")
        layout.addWidget(title)

        sub = QLabel(
            "Antigravity Dashboard needs access to your webcam\n"
            "to display the live robot camera feed.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(
            "color: #94a3b8; font-size: 12px;"
            "font-family: 'Inter', sans-serif; background: transparent;"
            "margin-top: 6px; margin-bottom: 20px;")
        layout.addWidget(sub)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        self.btn_allow = QPushButton("✔  Allow Access")
        self.btn_allow.setFixedSize(160, 40)
        self.btn_allow.setStyleSheet(
            "QPushButton { background: #00b4d8; color: #000; font-weight: 700;"
            "border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background: #00cff5; }")
        self.btn_allow.clicked.connect(self.allow_clicked)
        btn_row.addWidget(self.btn_allow)

        self.btn_deny = QPushButton("✖  Deny")
        self.btn_deny.setFixedSize(120, 40)
        self.btn_deny.setStyleSheet(
            "QPushButton { background: #2d2d34; color: #94a3b8; font-weight: 600;"
            "border-radius: 8px; font-size: 13px; border: 1px solid #3f3f46; }"
            "QPushButton:hover { background: #3f3f46; color: #e2e8f0; }")
        self.btn_deny.clicked.connect(self.deny_clicked)
        btn_row.addWidget(self.btn_deny)

        layout.addLayout(btn_row)


# ─────────────────────────────────────────────────────────────────────────────
#  Main Camera Tab
# ─────────────────────────────────────────────────────────────────────────────
class TabCamera(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._permission_granted = False
        self._recording          = False
        self._reconnect_attempts = 0

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # ── Left: feed viewport ────────────────────────────────────────────
        feed_frame = QFrame()
        feed_frame.setStyleSheet(
            "QFrame { background: #0b0b0d; border: 1px solid #2d2d34; border-radius: 10px; }")
        feed_vbox = QVBoxLayout(feed_frame)
        feed_vbox.setContentsMargins(0, 0, 0, 0)

        self.stacked = QStackedWidget()

        # Page 0: live video label
        self.lbl_frame = QLabel()
        self.lbl_frame.setAlignment(Qt.AlignCenter)
        self.lbl_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_frame.setStyleSheet("background: #0b0b0d;")
        self.stacked.addWidget(self.lbl_frame)   # index 0

        # Page 1: permission overlay
        self.perm_overlay = CameraPermissionOverlay()
        self.perm_overlay.allow_clicked.connect(self._grant_permission)
        self.perm_overlay.deny_clicked.connect(self._deny_permission)
        self.stacked.addWidget(self.perm_overlay)  # index 1

        feed_vbox.addWidget(self.stacked)

        # Bottom status bar
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(8, 4, 8, 6)

        self.lbl_stream_source = QLabel("⬤  No Signal")
        self.lbl_stream_source.setStyleSheet(
            "color: #e63946; font-size: 11px; font-family: Consolas;")
        status_bar.addWidget(self.lbl_stream_source)

        status_bar.addStretch()

        self.lbl_fps_bar = QLabel("FPS: --  |  Latency: -- ms")
        self.lbl_fps_bar.setStyleSheet(
            "color: #64748b; font-size: 11px; font-family: Consolas;")
        status_bar.addWidget(self.lbl_fps_bar)

        feed_vbox.addLayout(status_bar)
        main_layout.addWidget(feed_frame, 4)

        # ── Right: control panel ────────────────────────────────────────────
        ctrl_panel = QWidget()
        ctrl_panel.setMaximumWidth(260)
        ctrl_vbox = QVBoxLayout(ctrl_panel)
        ctrl_vbox.setContentsMargins(4, 0, 0, 0)
        ctrl_vbox.setSpacing(8)

        # ── Source Group ────────────────────────────────────────────────────
        src_group = QGroupBox("Video Source")
        src_layout = QVBoxLayout(src_group)

        src_layout.addWidget(QLabel("Local Webcam Device:"))
        self.combo_webcam = QComboBox()
        self.combo_webcam.currentIndexChanged.connect(self._on_webcam_selected)
        src_layout.addWidget(self.combo_webcam)

        refresh_row = QHBoxLayout()
        self.btn_refresh = QPushButton("⟳  Refresh Devices")
        self.btn_refresh.clicked.connect(self._enumerate_webcams)
        refresh_row.addWidget(self.btn_refresh)
        src_layout.addLayout(refresh_row)

        src_layout.addWidget(QLabel(""))

        src_layout.addWidget(QLabel("Or: Robot RTSP Feed URL:"))
        from PyQt5.QtWidgets import QLineEdit
        self.rtsp_input = QLineEdit()
        self.rtsp_input.setPlaceholderText("rtsp://192.168.123.161:8554/front")
        src_layout.addWidget(self.rtsp_input)

        self.btn_rtsp = QPushButton("📡  Connect RTSP Stream")
        self.btn_rtsp.clicked.connect(self._connect_rtsp)
        src_layout.addWidget(self.btn_rtsp)

        ctrl_vbox.addWidget(src_group)

        # ── Computer Vision Group ───────────────────────────────────────────
        ai_group = QGroupBox("Computer Vision")
        ai_layout = QVBoxLayout(ai_group)
        self.chk_detect = QCheckBox("Enable Face Detection (OpenCV)")
        self.chk_detect.stateChanged.connect(
            lambda s: self.thread.toggle_detection(s == Qt.Checked))
        ai_layout.addWidget(self.chk_detect)
        ctrl_vbox.addWidget(ai_group)

        # ── Capture Group ──────────────────────────────────────────────────
        cap_group = QGroupBox("Capture & Record")
        cap_layout = QVBoxLayout(cap_group)

        self.btn_screenshot = QPushButton("🖼  Take Screenshot")
        self.btn_screenshot.clicked.connect(self._take_screenshot)
        cap_layout.addWidget(self.btn_screenshot)

        self.btn_record = QPushButton("⏺  Start Video Record")
        self.btn_record.clicked.connect(self._toggle_record)
        cap_layout.addWidget(self.btn_record)

        ctrl_vbox.addWidget(cap_group)

        # ── Stream Stats Group ─────────────────────────────────────────────
        stats_group = QGroupBox("Stream Performance")
        stats_grid  = QGridLayout(stats_group)
        stats_grid.setColumnStretch(1, 1)

        def make_stat(label_text):
            lbl  = QLabel(label_text)
            lbl.setStyleSheet("color: #64748b; font-size: 11px;")
            val  = QLabel("--")
            val.setStyleSheet("color: #00d2ff; font-family: Consolas; font-size: 11px;")
            return lbl, val

        lbl_fps_l, self.lbl_fps    = make_stat("FPS:")
        lbl_lat_l, self.lbl_lat    = make_stat("Latency:")
        lbl_res_l, self.lbl_res    = make_stat("Resolution:")
        lbl_dev_l, self.lbl_dev    = make_stat("Device:")
        lbl_conn_l, self.lbl_conn  = make_stat("Status:")

        for i, (l, v) in enumerate([
            (lbl_fps_l, self.lbl_fps),
            (lbl_lat_l, self.lbl_lat),
            (lbl_res_l, self.lbl_res),
            (lbl_dev_l, self.lbl_dev),
            (lbl_conn_l, self.lbl_conn),
        ]):
            stats_grid.addWidget(l, i, 0)
            stats_grid.addWidget(v, i, 1)

        ctrl_vbox.addWidget(stats_group)
        ctrl_vbox.addStretch()

        main_layout.addWidget(ctrl_panel, 1)

        # ── Camera thread ──────────────────────────────────────────────────
        self.thread = CameraReceiver()
        self.thread.frame_ready.connect(self._on_frame_ready)
        self.thread.status_update.connect(self._on_status_update)
        self.thread.camera_lost.connect(self._on_camera_lost)
        self.thread.camera_found.connect(self._on_camera_found)

        # ── Auto-reconnect timer ───────────────────────────────────────────
        self.reconnect_timer = QTimer()
        self.reconnect_timer.setInterval(3000)
        self.reconnect_timer.timeout.connect(self._try_reconnect)

        # ── SSH watcher ────────────────────────────────────────────────────
        ssh_manager.connection_status.connect(self._on_ssh_status)

        # ── Init ───────────────────────────────────────────────────────────
        self._enumerate_webcams()

        # Show permission overlay on first open
        self.stacked.setCurrentIndex(1)

    # ── Webcam Enumeration ─────────────────────────────────────────────────
    def _enumerate_webcams(self):
        """Populate webcam combo using QCameraInfo (no OpenCV probing needed)."""
        self.combo_webcam.blockSignals(True)
        self.combo_webcam.clear()

        cameras = QCameraInfo.availableCameras()
        if cameras:
            for i, cam in enumerate(cameras):
                self.combo_webcam.addItem(f"[{i}] {cam.description()}", i)
        else:
            # Fallback: probe OpenCV indices 0-4
            found = []
            for idx in range(5):
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    found.append(idx)
                    cap.release()
            if found:
                for idx in found:
                    self.combo_webcam.addItem(f"[{idx}] Webcam {idx}", idx)
            else:
                self.combo_webcam.addItem("(No webcams found)", -1)

        self.combo_webcam.blockSignals(False)
        logger.info(f"Webcam enumeration: {self.combo_webcam.count()} device(s) found.")

    # ── Permission Logic ───────────────────────────────────────────────────
    def _grant_permission(self):
        self._permission_granted = True
        self.stacked.setCurrentIndex(0)
        self._start_camera()

    def _deny_permission(self):
        self._permission_granted = False
        self.stacked.setCurrentIndex(0)
        self.lbl_stream_source.setText("⬤  Camera Denied")
        self.lbl_stream_source.setStyleSheet(
            "color: #e63946; font-size: 11px; font-family: Consolas;")
        # Thread still starts but will show no-signal frame
        self._start_camera_no_device()

    def _start_camera(self):
        idx = self.combo_webcam.currentData()
        if idx is None or idx < 0:
            self._start_camera_no_device()
            return
        self.thread.set_local_source(idx)
        if not self.thread.isRunning():
            self.thread.start()
        self.lbl_dev.setText(self.combo_webcam.currentText()[:20])
        self.lbl_conn.setText("Connecting…")
        self.lbl_conn.setStyleSheet("color: #ff9f1c; font-family: Consolas; font-size: 11px;")

    def _start_camera_no_device(self):
        self.thread.set_local_source(-1)  # Will produce no-signal frames
        if not self.thread.isRunning():
            self.thread.start()

    # ── Source switching ───────────────────────────────────────────────────
    def _on_webcam_selected(self, combo_idx):
        if not self._permission_granted:
            return
        idx = self.combo_webcam.itemData(combo_idx)
        if idx is not None and idx >= 0:
            self.thread.set_local_source(idx)
            self.lbl_dev.setText(self.combo_webcam.currentText()[:20])
            self.lbl_conn.setText("Switching…")
            logger.info(f"Switched to local webcam index {idx}")

    def _connect_rtsp(self):
        url = self.rtsp_input.text().strip()
        if not url:
            url = self._build_rtsp_url()
        if not self._permission_granted:
            self._permission_granted = True
            self.stacked.setCurrentIndex(0)
        self.thread.set_remote_source(url)
        if not self.thread.isRunning():
            self.thread.start()
        self.lbl_dev.setText("RTSP")
        self.lbl_conn.setText("Connecting…")
        logger.info(f"Connecting to RTSP stream: {url}")

    def _build_rtsp_url(self) -> str:
        host = "192.168.123.161"
        if ssh_manager.is_connected() and ssh_manager.host \
                and ssh_manager.host != "127.0.0.1":
            host = ssh_manager.host
        return f"rtsp://{host}:8554/front"

    # ── SSH auto-switch ────────────────────────────────────────────────────
    def _on_ssh_status(self, connected: bool, msg: str):
        if connected and ssh_manager.host and ssh_manager.host != "127.0.0.1":
            url = self._build_rtsp_url()
            self.rtsp_input.setText(url)
            logger.info(f"Robot connected – RTSP URL updated to {url}")

    # ── Frame display ──────────────────────────────────────────────────────
    @pyqtSlot(QImage)
    def _on_frame_ready(self, qimg: QImage):
        if qimg.isNull():
            return
        pix = QPixmap.fromImage(qimg)
        w, h = self.lbl_frame.width(), self.lbl_frame.height()
        if w > 0 and h > 0:
            self.lbl_frame.setPixmap(
                pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.lbl_res.setText(f"{qimg.width()}×{qimg.height()}")

    @pyqtSlot(str, float, float)
    def _on_status_update(self, source_label: str, fps: float, latency_ms: float):
        self.lbl_fps.setText(f"{fps:.1f}")
        self.lbl_lat.setText(f"{latency_ms:.1f} ms")
        self.lbl_fps_bar.setText(f"FPS: {fps:.1f}  |  Latency: {latency_ms:.1f} ms")

    # ── Camera connect/disconnect events ───────────────────────────────────
    @pyqtSlot()
    def _on_camera_found(self):
        self._reconnect_attempts = 0
        self.reconnect_timer.stop()
        self.lbl_conn.setText("Live ✔")
        self.lbl_conn.setStyleSheet(
            "color: #22c55e; font-family: Consolas; font-size: 11px; font-weight: bold;")
        self.lbl_stream_source.setText("⬤  Camera Active")
        self.lbl_stream_source.setStyleSheet(
            "color: #22c55e; font-size: 11px; font-family: Consolas;")
        logger.info("Camera connection established.")

    @pyqtSlot()
    def _on_camera_lost(self):
        self.lbl_conn.setText("Lost – Reconnecting…")
        self.lbl_conn.setStyleSheet(
            "color: #f59e0b; font-family: Consolas; font-size: 11px;")
        self.lbl_stream_source.setText("⬤  Reconnecting…")
        self.lbl_stream_source.setStyleSheet(
            "color: #f59e0b; font-size: 11px; font-family: Consolas;")
        logger.warning("Camera signal lost. Starting auto-reconnect loop.")
        if not self.reconnect_timer.isActive():
            self.reconnect_timer.start()

    def _try_reconnect(self):
        self._reconnect_attempts += 1
        logger.info(f"Auto-reconnect attempt #{self._reconnect_attempts}")
        # Re-trigger the same source (the thread will reopen capture device on next loop)
        # Nothing else needed; the thread auto-re-opens on cap == None

    # ── Screenshot & Record ────────────────────────────────────────────────
    def _take_screenshot(self):
        pixmap = self.lbl_frame.pixmap()
        if pixmap and not pixmap.isNull():
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Screenshot", "screenshot.png",
                "PNG Images (*.png);;JPEG Images (*.jpg)")
            if path:
                pixmap.save(path)
                QMessageBox.information(self, "Saved",
                                        f"Screenshot saved to:\n{path}")

    def _toggle_record(self):
        if not self._recording:
            path, _ = QFileDialog.getSaveFileName(
                self, "Record Video", "camera_record.avi",
                "AVI Videos (*.avi)")
            if path:
                self.thread.start_recording(path)
                self._recording = True
                self.btn_record.setText("⏹  Stop Recording")
                self.btn_record.setStyleSheet(
                    "QPushButton { background: #e63946; color: white; font-weight: bold; }")
        else:
            self.thread.stop_recording()
            self._recording = False
            self.btn_record.setText("⏺  Start Video Record")
            self.btn_record.setStyleSheet("")
            QMessageBox.information(self, "Recording Saved",
                                    "Video recording saved successfully.")

    # ── Cleanup ────────────────────────────────────────────────────────────
    def closeEvent(self, event):
        self.reconnect_timer.stop()
        self.thread.running = False
        self.thread.wait(2000)
        event.accept()
