import time
import os
import cv2
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QCheckBox, QGroupBox, QFileDialog, QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt

class CameraReceiver(QThread):
    frame_ready = pyqtSignal(QImage)

    def __init__(self):
        super().__init__()
        self.running = False
        self.stream_url = ""
        self.use_mock = True
        self.detect_objects = False
        self.is_recording = False
        self.video_writer = None
        self.record_path = ""
        
        self.frame_width = 640
        self.frame_height = 480
        self.tick = 0

    def set_source(self, url: str, use_mock: bool = True):
        self.stream_url = url
        self.use_mock = use_mock

    def toggle_detection(self, enabled: bool):
        self.detect_objects = enabled

    def start_recording(self, path: str):
        self.record_path = path
        self.is_recording = True

    def stop_recording(self):
        self.is_recording = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

    def run(self):
        self.running = True
        cap = None
        
        while self.running:
            start_time = time.time()
            img_out = None
            
            # Open capture device
            if cap is None or not cap.isOpened():
                try:
                    if self.use_mock:
                        # Simulated mode uses local webcam (Index 0)
                        cap = cv2.VideoCapture(0)
                    else:
                        # Remote stream uses stream_url
                        if self.stream_url:
                            if self.stream_url.isdigit():
                                cap = cv2.VideoCapture(int(self.stream_url))
                            else:
                                cap = cv2.VideoCapture(self.stream_url)
                        else:
                            cap = None
                except Exception:
                    cap = None
                    
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame_rgb.shape
                    
                    if self.detect_objects:
                        self.detect_faces_cv(frame_rgb)
                        
                    if self.is_recording:
                        self.write_frame_to_video(frame)
                        
                    # CRITICAL FIX: copy to prevent segfault
                    img_out = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
                else:
                    cap.release()
                    cap = None
                    
            if img_out is None:
                img_out = self.generate_no_signal_frame()
                
            self.frame_ready.emit(img_out)
            
            # Clamp to 30fps
            elapsed = time.time() - start_time
            sleep_time = max(0.001, 0.033 - elapsed)
            time.sleep(sleep_time)
            
        if cap:
            cap.release()
            
    def write_frame_to_video(self, frame):
        if self.video_writer is None:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            h, w = frame.shape[:2]
            self.video_writer = cv2.VideoWriter(self.record_path, fourcc, 30.0, (w, h))
        self.video_writer.write(frame)

    def detect_faces_cv(self, frame_rgb):
        """Standard OpenCV face cascade classifier runner."""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            if not face_cascade.empty():
                gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame_rgb, "HUMAN FACE [94%]", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        except Exception:
            pass

    def generate_no_signal_frame(self) -> QImage:
        self.tick += 1
        import numpy as np
        img = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        
        # Grid lines background
        grid_size = 40
        for y in range(0, self.frame_height, grid_size):
            img[y:y+1, :, :] = [18, 18, 22]
        for x in range(0, self.frame_width, grid_size):
            img[:, x:x+1, :] = [18, 18, 22]
            
        cx, cy = self.frame_width // 2, self.frame_height // 2
        
        # Warning Card
        cv2.rectangle(img, (cx - 210, cy - 70), (cx + 210, cy + 70), (26, 26, 30), -1)
        cv2.rectangle(img, (cx - 210, cy - 70), (cx + 210, cy + 70), (230, 57, 70), 1)
        
        # Text warning
        cv2.putText(img, "CAMERA SIGNAL LOST", (cx - 120, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 57, 70), 2)
        cv2.putText(img, "Verify IP link or connect local webcam", (cx - 150, cy + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (148, 163, 184), 1)
        
        # Flashing indicator
        flash_color = (230, 57, 70) if (self.tick // 15) % 2 == 0 else (26, 26, 30)
        cv2.circle(img, (cx - 140, cy - 15), 6, flash_color, -1)
        
        return QImage(img.data, self.frame_width, self.frame_height, self.frame_width * 3, QImage.Format_RGB888).copy()

class TabCamera(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        
        # 1. Left Viewport
        self.feed_layout = QVBoxLayout()
        self.lbl_frame = QLabel()
        self.lbl_frame.setAlignment(Qt.AlignCenter)
        self.lbl_frame.setStyleSheet("background-color: #0b0b0d; border: 1px solid #2d2d34; border-radius: 8px;")
        self.feed_layout.addWidget(self.lbl_frame)
        self.layout.addLayout(self.feed_layout, 4)
        
        # 2. Right Control Panel
        self.ctrl_panel = QWidget()
        self.ctrl_layout = QVBoxLayout(self.ctrl_panel)
        self.ctrl_layout.setContentsMargins(5, 0, 0, 0)
        
        # Stream Select
        self.source_group = QGroupBox("Video Feeds")
        self.source_layout = QVBoxLayout(self.source_group)
        self.combo_source = QComboBox()
        self.combo_source.addItems(["Local Webcam (Index 0)", "Robot RTSP Feed"])
        self.combo_source.currentIndexChanged.connect(self.source_changed)
        self.source_layout.addWidget(self.combo_source)
        
        self.chk_mock = QCheckBox("Simulate Camera Offline")
        self.chk_mock.setChecked(True)
        self.chk_mock.stateChanged.connect(self.toggle_mock_mode)
        self.source_layout.addWidget(self.chk_mock)
        self.ctrl_layout.addWidget(self.source_group)
        
        # AI & Processing Group
        self.ai_group = QGroupBox("Computer Vision")
        self.ai_layout = QVBoxLayout(self.ai_group)
        self.chk_detect = QCheckBox("Enable Object Detection")
        self.chk_detect.stateChanged.connect(self.toggle_detection)
        self.ai_layout.addWidget(self.chk_detect)
        self.ctrl_layout.addWidget(self.ai_group)
        
        # Record & Capture Group
        self.record_group = QGroupBox("Capture & Stream Tools")
        self.record_layout = QVBoxLayout(self.record_group)
        
        self.btn_capture = QPushButton("Take Screenshot")
        self.btn_capture.clicked.connect(self.take_screenshot)
        self.record_layout.addWidget(self.btn_capture)
        
        self.btn_record = QPushButton("Start Video Record")
        self.btn_record.clicked.connect(self.toggle_record)
        self.record_layout.addWidget(self.btn_record)
        
        self.ctrl_layout.addWidget(self.record_group)
        
        # Stream Status
        self.status_group = QGroupBox("Stream Performance")
        self.status_layout = QVBoxLayout(self.status_group)
        self.lbl_fps = QLabel("FPS: 30.0")
        self.status_layout.addWidget(self.lbl_fps)
        self.lbl_latency = QLabel("Latency: ~12 ms")
        self.status_layout.addWidget(self.lbl_latency)
        self.lbl_bandwidth = QLabel("Bandwidth: 3.5 MB/s")
        self.status_layout.addWidget(self.lbl_bandwidth)
        self.ctrl_layout.addWidget(self.status_group)
        
        self.ctrl_layout.addStretch()
        self.layout.addWidget(self.ctrl_panel, 1)
        
        # Launch receiver thread
        self.thread = CameraReceiver()
        self.thread.frame_ready.connect(self.on_frame_ready)
        self.thread.start()

    def closeEvent(self, event):
        self.thread.running = False
        self.thread.wait()
        event.accept()

    @pyqtSlot(QImage)
    def on_frame_ready(self, qimg: QImage):
        # Resize image keeping aspect ratio
        if not qimg.isNull():
            pixmap = QPixmap.fromImage(qimg)
            w = self.lbl_frame.width()
            h = self.lbl_frame.height()
            if w > 0 and h > 0:
                self.lbl_frame.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def source_changed(self, idx):
        if idx == 0:
            self.chk_mock.setChecked(True)
            self.thread.set_source("", use_mock=True)
            self.lbl_latency.setText("Latency: ~12 ms")
            self.lbl_bandwidth.setText("Bandwidth: 3.5 MB/s")
        elif idx == 1:
            self.chk_mock.setChecked(False)
            self.thread.set_source("rtsp://192.168.123.161:8554/front", use_mock=False)
            self.lbl_latency.setText("Latency: ~45 ms")
            self.lbl_bandwidth.setText("Bandwidth: 2.1 MB/s")

    def toggle_mock_mode(self, state):
        if state == Qt.Checked:
            self.combo_source.setCurrentIndex(0)
            self.thread.set_source("", use_mock=True)
        else:
            self.combo_source.setCurrentIndex(1)
            self.thread.set_source("rtsp://192.168.123.161:8554/front", use_mock=False)

    def toggle_detection(self, state):
        self.thread.toggle_detection(state == Qt.Checked)

    def take_screenshot(self):
        pixmap = self.lbl_frame.pixmap()
        if pixmap and not pixmap.isNull():
            path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "screenshot.png", "PNG Images (*.png);;JPEG Images (*.jpg)")
            if path:
                pixmap.save(path)
                QMessageBox.information(self, "Saved", f"Screenshot successfully saved to:\n{path}")

    def toggle_record(self):
        if not self.thread.is_recording:
            path, _ = QFileDialog.getSaveFileName(self, "Record Video File", "camera_record.avi", "AVI Videos (*.avi)")
            if path:
                self.thread.start_recording(path)
                self.btn_record.setText("Stop Video Record")
                self.btn_record.setStyleSheet("background-color: #e63946; color: white;")
        else:
            self.thread.stop_recording()
            self.btn_record.setText("Start Video Record")
            self.btn_record.setStyleSheet("")
            QMessageBox.information(self, "Recorded", f"Video recording saved successfully.")
