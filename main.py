"""
PredatorAlert Main Controller
Optimized for Raspberry Pi 5: minimal frame copies, throttled streaming, efficient loops.
"""
import time
import signal
import sys
import threading
import cv2
import numpy as np
from typing import Optional
from flask import Flask, Response

from config import Config
from logger import detection_logger
from camera import Camera
from detector import WildlifeDetector, Detection
from classifier import AnimalClassifier, ClassifiedDetection
from api_client import APIClient
from sms_notifier import SMSNotifier

# Flask app for streaming
app = Flask(__name__)
# Create placeholder frame
output_frame = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.putText(output_frame, "Initializing Camera...", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
lock = threading.Lock()

# Pre-calculate stream interval from config (avoid repeated division)
_stream_interval = 1.0 / max(Config.STREAM_FPS, 1)

def generate_frames():
    """Generate MJPEG frames for web streaming, throttled to STREAM_FPS."""
    global output_frame, lock
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]  # Lower quality for stream = less CPU
    while True:
        with lock:
            if output_frame is None:
                time.sleep(_stream_interval)
                continue
            flag, encoded = cv2.imencode(".jpg", output_frame, encode_params)
            if not flag:
                continue
        
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encoded) + b'\r\n')
        
        # Throttle to configured FPS (default 10 FPS = 0.1s)
        time.sleep(_stream_interval)

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/")
def index():
    return "PredatorAlert Live Feed <br> <img src='/video_feed' width='640' />"


class PredatorAlertApp:
    """Main application controller for PredatorAlert edge device.
    
    Optimized for Pi 5:
    - Single frame copy for display (not per-capture)
    - Throttled display loop to match stream FPS
    - Detection runs on main thread at configured interval
    """
    
    def __init__(self):
        self.camera: Optional[Camera] = None
        self.detector: Optional[WildlifeDetector] = None
        self.classifier: Optional[AnimalClassifier] = None
        self.api_client: Optional[APIClient] = None
        self.sms_notifier: Optional[SMSNotifier] = None
        self._running = False
        self._latest_detections: list = []
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        detection_logger.log_shutdown()
        self._running = False
    
    def initialize(self) -> bool:
        """Initialize all components."""
        detection_logger.log_startup()
        
        # Validate configuration
        config_errors = Config.validate()
        if config_errors:
            for error in config_errors:
                detection_logger.log_error(f"Configuration error: {error}")
            return False
        
        # Initialize camera
        self.camera = Camera()
        if not self.camera.connect():
            detection_logger.log_error("Failed to initialize camera")
            return False
        
        # Initialize detector
        self.detector = WildlifeDetector()
        if not self.detector.initialize():
            detection_logger.log_error("Failed to initialize detector")
            return False
        
        # Initialize classifier
        self.classifier = AnimalClassifier()
        
        # Initialize API client
        self.api_client = APIClient()
        self.api_client.start()
        
        # Initialize SMS notifier
        self.sms_notifier = SMSNotifier()
        if not self.sms_notifier.initialize():
            detection_logger.log_error("SMS notifier failed to initialize (alerts will continue without SMS)")
        
        detection_logger.log_api_status("All components initialized successfully")
        return True
    
    def run(self) -> None:
        """Run the main application loops."""
        if not self.initialize():
            detection_logger.log_error("Initialization failed, exiting")
            sys.exit(1)
        
        self._running = True
        detection_logger.log_api_status(
            "PredatorAlert starting",
            f"device_id={Config.DEVICE_ID} | imgsz={Config.INFERENCE_IMGSZ} | stream=http://0.0.0.0:{Config.STREAM_PORT}"
        )

        # Start Web Stream in background
        t_web = threading.Thread(
            target=lambda: app.run(host="0.0.0.0", port=Config.STREAM_PORT, debug=False, use_reloader=False),
            daemon=True
        )
        t_web.start()
        
        # Start Display Loop (matches stream FPS, not 30 FPS)
        t_display = threading.Thread(target=self._display_loop, daemon=True)
        t_display.start()

        # Main Thread: Detection Loop (AI Speed)
        try:
            last_heartbeat = time.time()
            last_detection_time = 0
            
            while self._running:
                now = time.time()
                
                # Throttle detection frequency to prevent overheating
                if now - last_detection_time >= Config.DETECTION_INTERVAL_SECONDS:
                    self._detection_cycle()
                    last_detection_time = now
                else:
                    # Sleep remaining time instead of busy-polling
                    remaining = Config.DETECTION_INTERVAL_SECONDS - (now - last_detection_time)
                    time.sleep(min(remaining, 0.1))
                
                # Heartbeat log every 30 seconds (reduced from 10 to cut I/O)
                if now - last_heartbeat > 30:
                    detection_logger.log_heartbeat()
                    last_heartbeat = now
                
        except Exception as e:
            detection_logger.log_error("Detection loop error", e)
        finally:
            self.shutdown()

    def _display_loop(self) -> None:
        """Dedicated thread for updating the video feed at stream FPS.
        
        Runs at STREAM_FPS (default 10) instead of 30 to reduce CPU usage.
        Only copies frame when drawing detection overlays.
        """
        display_interval = _stream_interval
        
        while self._running:
            try:
                # Get latest raw frame (no copy from camera)
                frame = self.camera.capture_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue

                # Draw detections and update stream buffer
                try:
                    self._update_gui(frame, self._latest_detections)
                except Exception:
                    pass  # Avoid race conditions causing crashes

                # Match stream FPS
                time.sleep(display_interval)
                
            except Exception as e:
                detection_logger.log_error("Display loop error", e)
                time.sleep(0.5)

    def _detection_cycle(self) -> None:
        """Execute a single detection cycle."""
        # Get frame reference (no copy needed for detection)
        frame = self.camera.capture_frame()
        if frame is None:
            time.sleep(0.1)
            return
        
        # Run detection
        detections = self.detector.detect(frame)
        
        # Classify detections
        classified = self.classifier.classify_batch(detections)
        
        # Update shared state for display thread
        self._latest_detections = classified
        
        # Process alerts
        for detection in classified:
            self._process_detection(detection, frame)
    
    def _process_detection(
        self,
        detection: ClassifiedDetection,
        frame: np.ndarray
    ) -> None:
        """Process a classified detection — send API alert and SMS for predators."""
        if detection.is_predator:
            # Predator detected - send with image
            success = self.api_client.send_detection(
                animal=detection.class_name,
                confidence=detection.confidence,
                frame=frame,
                is_predator=True
            )
            
            # Send SMS alert
            if self.sms_notifier and self.sms_notifier.is_ready():
                self.sms_notifier.send_predator_alert(
                    animal=detection.class_name,
                    confidence=detection.confidence,
                    priority_label=detection.priority_label
                )
            
            api_status = "sent" if success else "queued"
            detection_logger.log_detection(
                animal=detection.class_name,
                confidence=detection.confidence,
                is_predator=True,
                priority=detection.priority,
                api_status=api_status
            )
            
        elif detection.confidence > Config.SAFE_ANIMAL_THRESHOLD:
            # High-confidence safe animal - send without image
            success = self.api_client.send_detection(
                animal=detection.class_name,
                confidence=detection.confidence,
                frame=None,
                is_predator=False
            )
            
            api_status = "sent" if success else "queued"
            detection_logger.log_detection(
                animal=detection.class_name,
                confidence=detection.confidence,
                is_predator=False,
                priority=None,
                api_status=api_status
            )

    def _update_gui(self, frame: np.ndarray, detections: list) -> None:
        """Draw detections and update shared buffer for streaming/GUI.
        
        Only copies frame once for display overlay — original frame untouched.
        """
        # Only copy if we need to draw overlays
        if detections:
            display_frame = frame.copy()
            
            for d in detections:
                x, y, w, h = d.bbox
                color = (0, 0, 255) if d.is_predator else (0, 255, 0)
                
                cv2.rectangle(display_frame, (x - w//2, y - h//2), 
                            (x + w//2, y + h//2), color, 2)
                
                label = f"{d.class_name} {d.confidence:.2f}"
                cv2.putText(display_frame, label, (x - w//2, y - h//2 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        else:
            display_frame = frame
        
        # Update global frame for web streaming (swap reference, no copy)
        global output_frame, lock
        with lock:
            output_frame = display_frame

        # Update local GUI window if enabled
        if Config.GUI_ENABLED:
            try:
                cv2.imshow("PredatorAlert Main", display_frame)
                cv2.waitKey(1)
            except Exception:
                pass
    
    def shutdown(self) -> None:
        """Cleanup and shutdown all components."""
        self._running = False
        
        if self.api_client:
            pending = self.api_client.get_queue_size()
            if pending > 0:
                detection_logger.log_api_status(f"Pending requests in queue: {pending}")
            self.api_client.stop()
        
        if self.camera:
            self.camera.disconnect()
        
        detection_logger.log_shutdown()


def main():
    """Application entry point."""
    app = PredatorAlertApp()
    app.run()


if __name__ == "__main__":
    main()
