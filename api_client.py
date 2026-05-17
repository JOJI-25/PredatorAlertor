"""
PredatorAlert API Client Module
Optimized for INSTANT alert delivery to backend.
- Fast alert (no image) sent immediately in separate thread
- Image follows separately if needed
- Reduced timeouts for faster failure recovery
- Parallel sending — alerts never block each other
"""
import base64
import time
import threading
import queue
import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Optional
import requests
import cv2
import numpy as np
from dataclasses import dataclass, asdict
from config import Config
from logger import detection_logger


@dataclass
class DetectionPayload:
    """Payload structure for API requests."""
    device_id: str
    animal: str
    confidence: float
    timestamp: str
    image_base64: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary, excluding empty values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v}


class APIClient:
    """HTTP client for sending detections to backend API.
    
    Optimized for instant alerts:
    - Predator alerts sent IMMEDIATELY (no queue wait) without image
    - Image sent separately afterward (doesn't delay the alert)
    - Fast timeout (10s) — don't wait forever for slow servers
    - Background worker handles non-urgent detections
    """
    
    def __init__(self):
        self.base_url = Config.API_URL.rstrip("/")
        self.api_key = Config.API_KEY
        self.timeout = min(Config.API_TIMEOUT, 15)  # Cap at 15s for fast alerts
        self.max_retries = Config.API_RETRIES
        
        # Queue for non-urgent detections (safe animals)
        self._outgoing_queue: queue.Queue = queue.Queue()
        self._sender_thread: Optional[threading.Thread] = None
        self._running = False
        
        # SQLite offline cache
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline_cache.db")
        self._init_db()
        
        # Session for connection pooling (reuses TCP connections = faster)
        self.session = requests.Session()
        # Pre-warm: set keep-alive and connection pool
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=2,
            pool_maxsize=4,
            max_retries=0  # We handle retries ourselves
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    def _init_db(self) -> None:
        """Initialize SQLite database for offline caching."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS offline_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        payload TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        except Exception as e:
            detection_logger.log_error("Failed to initialize offline cache DB", e)

    def _cache_payload(self, payload_dict: dict) -> None:
        """Save a failed payload to the local SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO offline_queue (payload) VALUES (?)', (json.dumps(payload_dict),))
                conn.commit()
            detection_logger.log_api_status("Payload cached offline for later sync")
        except Exception as e:
            detection_logger.log_error("Failed to cache payload offline", e)

    @property
    def headers(self) -> dict:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def start(self) -> None:
        """Start the background sender thread and wake up server."""
        self._running = True
        self._sender_thread = threading.Thread(target=self._sender_worker, daemon=True)
        self._sender_thread.start()
        
        # Trigger wake-up in background (critical for Render cold starts)
        threading.Thread(target=self._wake_up_server, daemon=True).start()
        
        detection_logger.log_api_status("Client started (Instant Alert Mode)")
        
    def _wake_up_server(self):
        """Ping the server root to wake it up from cold start."""
        try:
            detection_logger.log_api_status("Sending wake-up ping...")
            self.session.get(self.base_url, timeout=5)
        except Exception:
            pass  # Expected — just wake the server
    
    def stop(self) -> None:
        """Stop the background sender thread."""
        self._running = False
        if self._sender_thread is not None:
            self._sender_thread.join(timeout=5)
        self.session.close()
        detection_logger.log_api_status("Client stopped")
    
    def send_detection(
        self,
        animal: str,
        confidence: float,
        frame: Optional[np.ndarray] = None,
        is_predator: bool = False
    ) -> bool:
        """
        Send a detection event.
        
        PREDATORS: Sent INSTANTLY in a separate thread (no queue wait).
                   Alert goes first without image, image follows separately.
        SAFE:      Queued for background sending.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if is_predator:
            # INSTANT PATH: Send alert immediately in its own thread
            threading.Thread(
                target=self._send_predator_instant,
                args=(animal, confidence, timestamp, frame),
                daemon=True
            ).start()
        else:
            # QUEUE PATH: Non-urgent, send in background
            payload = DetectionPayload(
                device_id=Config.DEVICE_ID,
                animal=animal,
                confidence=round(confidence, 4),
                timestamp=timestamp
            )
            self._outgoing_queue.put(payload)
        
        return True
    
    def _send_predator_instant(
        self,
        animal: str,
        confidence: float,
        timestamp: str,
        frame: Optional[np.ndarray]
    ) -> None:
        """
        INSTANT predator alert — runs in its own thread.
        Step 1: Send alert WITHOUT image (tiny payload = instant delivery)
        Step 2: Send image separately (doesn't delay the alert)
        """
        # Step 1: FAST ALERT — no image, minimal payload
        fast_payload = DetectionPayload(
            device_id=Config.DEVICE_ID,
            animal=animal,
            confidence=round(confidence, 4),
            timestamp=timestamp
        )
        
        success = self._send_with_fast_timeout(fast_payload)
        
        if success:
            detection_logger.log_api_status(
                "INSTANT alert delivered",
                f"animal={animal} confidence={confidence:.2f}"
            )
        else:
            detection_logger.log_error(f"INSTANT alert failed for {animal}. Caching offline.")
            self._cache_payload(fast_payload.to_dict())
        
        # Step 2: Send image separately (if available)
        if frame is not None:
            image_payload = DetectionPayload(
                device_id=Config.DEVICE_ID,
                animal=animal,
                confidence=round(confidence, 4),
                timestamp=timestamp,
                image_base64=self._encode_frame(frame)
            )
            success = self._send_actual_request(image_payload)
            if not success:
                detection_logger.log_error(f"Image alert failed for {animal}. Caching offline.")
                self._cache_payload(image_payload.to_dict())
    
    def _send_with_fast_timeout(self, payload: DetectionPayload) -> bool:
        """Send with aggressive timeout for instant delivery. Single attempt."""
        url = f"{self.base_url}/api/detections"
        
        try:
            response = self.session.post(
                url,
                json=payload.to_dict(),
                headers=self.headers,
                timeout=10  # Fast timeout — don't wait forever
            )
            return response.status_code in (200, 201, 202)
        except Exception:
            return False
    
    def _send_actual_request(self, payload: DetectionPayload) -> bool:
        """Standard request with retries (for image payloads and safe animals)."""
        url = f"{self.base_url}/api/detections"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    url,
                    json=payload.to_dict(),
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if response.status_code in (200, 201, 202):
                    return True
                
                detection_logger.log_api_status(
                    "Request failed",
                    f"status={response.status_code} attempt={attempt + 1}"
                )
                
            except requests.exceptions.Timeout:
                detection_logger.log_error(f"Request timeout (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError as e:
                detection_logger.log_error(f"Connection error (attempt {attempt + 1})", e)
            except Exception as e:
                detection_logger.log_error(f"Request error (attempt {attempt + 1})", e)
            
            # Short backoff (1s, 2s) — not exponential, keep it fast
            if attempt < self.max_retries - 1:
                time.sleep(min(attempt + 1, 2))
        
        return False
    
    def _encode_frame(self, frame: np.ndarray) -> str:
        """Encode frame as JPEG and convert to base64."""
        try:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, Config.JPEG_QUALITY]
            _, buffer = cv2.imencode(".jpg", frame, encode_params)
            return base64.b64encode(buffer).decode("utf-8")
        except Exception as e:
            detection_logger.log_error("Frame encoding failed", e)
            return ""
    
    def _sender_worker(self) -> None:
        """Background worker for non-urgent (safe animal) detections and offline sync."""
        while self._running:
            try:
                # 1. Check in-memory queue first
                payload = self._outgoing_queue.get(timeout=1)
                success = self._send_actual_request(payload)
                
                if not success:
                    detection_logger.log_error("Failed to send detection after retries. Caching offline.")
                    self._cache_payload(payload.to_dict())
                
            except queue.Empty:
                pass
            except Exception as e:
                detection_logger.log_error("Sender worker error", e)
            
            # 2. When idle, attempt to sync offline cache
            if self._outgoing_queue.empty() and self._running:
                self._sync_offline_cache()
                
    def _sync_offline_cache(self) -> None:
        """Attempt to send cached payloads when connection is restored."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, payload FROM offline_queue ORDER BY id ASC LIMIT 5')
                rows = cursor.fetchall()
                
            if not rows:
                return  # Nothing to sync
                
            for row_id, payload_str in rows:
                if not self._running:
                    break
                    
                try:
                    payload_dict = json.loads(payload_str)
                    payload = DetectionPayload(**payload_dict)
                    
                    # Try sending with normal retries
                    success = self._send_actual_request(payload)
                    
                    if success:
                        with sqlite3.connect(self.db_path) as conn:
                            conn.cursor().execute('DELETE FROM offline_queue WHERE id = ?', (row_id,))
                            conn.commit()
                        detection_logger.log_api_status(f"Offline cache synced record {row_id}")
                    else:
                        # If still failing, connection is likely still down. Stop syncing.
                        break
                        
                except Exception:
                    # Drop corrupted JSON to prevent infinite blocks
                    with sqlite3.connect(self.db_path) as conn:
                        conn.cursor().execute('DELETE FROM offline_queue WHERE id = ?', (row_id,))
                        conn.commit()
                    
        except Exception:
            pass  # Ignore DB read errors during background sync
    
    def get_queue_size(self) -> int:
        """Get number of pending requests."""
        return self._outgoing_queue.qsize()
