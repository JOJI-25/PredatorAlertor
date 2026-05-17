"""
PredatorAlert Camera Module
Handles Pi Camera Module 3 frame capture using the native Picamera2 library.
Optimized for Raspberry Pi 5 — minimal memory allocation, zero-copy where possible.
"""
import time
import threading
import numpy as np
import cv2
from typing import Optional
from config import Config
from logger import detection_logger

# Try to import Picamera2 (Native Pi 5 Library)
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False


class Camera:
    """Pi Camera Module 3 frame capture using Picamera2 (Native) or OpenCV (Fallback).
    
    Optimized for Pi 5:
    - Double-buffer pattern to avoid frame.copy() on every read
    - BGR888 native format to avoid color conversion overhead
    """
    
    def __init__(self):
        self.picam2: Optional[Picamera2] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        # Double buffer: writer writes to _back_frame, reader reads _front_frame
        self._front_frame: Optional[np.ndarray] = None
        self._back_frame: Optional[np.ndarray] = None
        self._frame_ready = False
        self.mode = "none"  # 'picamera2', 'opencv', 'none'
    
    def connect(self) -> bool:
        """
        Initialize camera connection.
        Priority:
        1. Picamera2 (Native, High Performance, specific for Pi 5)
        2. OpenCV GStreamer (Backup)
        """
        self.threaded = Config.CAMERA_THREADED
        detection_logger.log_camera_status("Initializing Camera...")

        # STRATEGY 1: Native Picamera2 (The "Correct" way for Pi 5)
        if PICAMERA_AVAILABLE:
            try:
                detection_logger.log_camera_status("Attempting Native Picamera2 connection...")
                self.picam2 = Picamera2()
                
                # Configure for rapid capture
                # BGR888 is native for OpenCV (No conversion needed = Faster!)
                config = self.picam2.create_preview_configuration(
                    main={
                        "size": (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT),
                        "format": "BGR888"
                    }
                )
                self.picam2.configure(config)
                self.picam2.start()
                
                # Test capture
                test_frame = self.picam2.capture_array()
                if test_frame is not None and test_frame.size > 0:
                    detection_logger.log_camera_status("Success! Connected via Picamera2 (Native).")
                    self.mode = "picamera2"
                    self._start_thread()
                    return True
            except Exception as e:
                detection_logger.log_error("Picamera2 failed", e)
                if self.picam2:
                    self.picam2.stop()
                    self.picam2 = None
        else:
            detection_logger.log_camera_status("Picamera2 library not found. Falling back to OpenCV.")

        # STRATEGY 2: OpenCV GStreamer (Fallback)
        try:
            gst_pipeline = (
                f"libcamerasrc ! video/x-raw, width={Config.CAMERA_WIDTH}, height={Config.CAMERA_HEIGHT} "
                f"! videoconvert ! video/x-raw, format=BGR ! appsink drop=true sync=false"
            )
            detection_logger.log_camera_status(f"Attempting GStreamer fallback: {gst_pipeline}")
            
            self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
            if self.cap.isOpened():
                ret, _ = self.cap.read()
                if ret:
                    detection_logger.log_camera_status("Success! Connected via GStreamer.")
                    self.mode = "opencv"
                    self._start_thread()
                    return True
        except Exception as e:
            detection_logger.log_error("GStreamer fallback failed", e)

        detection_logger.log_error("CRITICAL: All camera methods failed.")
        return False

    def _start_thread(self):
        """Helper to start the background thread."""
        self._running = True
        if self.threaded:
            self._thread = threading.Thread(target=self._update, daemon=True)
            self._thread.start()
    
    def _update(self):
        """Background thread to continuously read frames.
        
        Writes to _back_frame, then swaps with _front_frame under lock.
        This avoids allocating new frames on every capture.
        """
        while self._running:
            try:
                frame = None
                
                if self.mode == "picamera2" and self.picam2:
                    # Native Capture — BGR888 format, no conversion needed
                    frame = self.picam2.capture_array()
                    
                elif self.mode == "opencv" and self.cap:
                    if not self.cap.isOpened():
                        break
                    ret, frame = self.cap.read()
                    if not ret:
                        frame = None

                if frame is not None:
                    with self._lock:
                        # Swap buffers — no copy needed
                        self._front_frame = frame
                        self._frame_ready = True
                else:
                    time.sleep(0.01)  # Avoid busy loop on fail
                    
            except Exception as e:
                detection_logger.log_error("Frame capture error", e)
                time.sleep(0.1)
                
    def capture_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame.
        
        Returns the frame directly (no copy) for display use.
        Callers that need to modify the frame should copy it themselves.
        """
        if not self._running:
            return None
        
        with self._lock:
            if not self._frame_ready or self._front_frame is None:
                return None
            return self._front_frame

    def disconnect(self) -> None:
        """Release camera resources."""
        self._running = False
        
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()
            self.picam2 = None
            
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        detection_logger.log_camera_status("Disconnected")
    
    def is_connected(self) -> bool:
        return self._running
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
