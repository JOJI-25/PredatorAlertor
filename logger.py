"""
PredatorAlert Logging Module
Provides structured file and journald-compatible logging for detection events.
"""
import logging
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from config import Config


class DetectionLogger:
    """Logger for detection events with structured output."""
    
    def __init__(self):
        self.logger = logging.getLogger("predatoralert")
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Configure file and console logging."""
        # Ensure log directory exists
        log_path = Path(Config.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logger level
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
        
        # File handler with JSON-compatible format
        file_handler = logging.FileHandler(Config.LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S%z'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler for journald compatibility
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_detection(
        self,
        animal: str,
        confidence: float,
        is_predator: bool,
        priority: int | None,
        api_status: str,
        image_url: str | None = None
    ) -> None:
        """Log a detection event with structured fields."""
        # Use f-string instead of json.dumps() for speed
        message = (
            f"animal={animal} confidence={confidence:.4f} "
            f"predator={is_predator} priority={priority} api_status={api_status}"
        )
        
        if is_predator:
            self.logger.warning(f"PREDATOR_DETECTED | {message}")
        else:
            self.logger.info(f"SAFE_ANIMAL | {message}")
    
    def log_startup(self) -> None:
        """Log application startup."""
        self.logger.info(f"PredatorAlert starting | device_id={Config.DEVICE_ID}")
    
    def log_shutdown(self) -> None:
        """Log application shutdown."""
        self.logger.info("PredatorAlert shutting down gracefully")
    
    def log_error(self, message: str, exc: Exception | None = None) -> None:
        """Log an error with optional exception details."""
        if exc:
            self.logger.error(f"{message} | error={str(exc)}")
        else:
            self.logger.error(message)
    
    def log_camera_status(self, status: str) -> None:
        """Log camera connection status."""
        self.logger.info(f"CAMERA | {status}")
    
    def log_api_status(self, status: str, details: str | None = None) -> None:
        """Log API communication status."""
        msg = f"API | {status}"
        if details:
            msg += f" | {details}"
        self.logger.info(msg)

    def log_heartbeat(self) -> None:
        """Log a periodic heartbeat to show system is alive."""
        self.logger.info("SYSTEM | Status: Active | Camera: OK | Scanning for predators...")


# Global logger instance
detection_logger = DetectionLogger()
