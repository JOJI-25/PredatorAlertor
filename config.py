"""
PredatorAlert Configuration Module
Loads all configuration from environment variables with sensible defaults.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    
    # Device identification
    DEVICE_ID: str = os.getenv("DEVICE_ID", "pi5-edge-001")
    GUI_ENABLED: bool = os.getenv("GUI_ENABLED", "True").lower() == "true"
    STREAM_PORT: int = int(os.getenv("STREAM_PORT", "5000"))
    STREAM_FPS: int = int(os.getenv("STREAM_FPS", "10"))  # Lower = less CPU heat
    
    # Backend API settings
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    API_KEY: str = os.getenv("API_KEY", "")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "60"))
    API_RETRIES: int = int(os.getenv("API_RETRIES", "3"))
    
    # Detection settings
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))
    SAFE_ANIMAL_THRESHOLD: float = float(os.getenv("SAFE_ANIMAL_THRESHOLD", "0.90"))
    DETECTION_INTERVAL_SECONDS: float = float(os.getenv("DETECTION_INTERVAL_SECONDS", "2"))
    
    # YOLO Model Settings (Optimized for Raspberry Pi 5)
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/5class.pt")
    # Input image size for inference (320 = fast on Pi 5, 640 = more accurate)
    INFERENCE_IMGSZ: int = int(os.getenv("INFERENCE_IMGSZ", "320"))
    
    # Camera settings
    CAMERA_WIDTH: int = int(os.getenv("CAMERA_WIDTH", "640"))
    CAMERA_HEIGHT: int = int(os.getenv("CAMERA_HEIGHT", "480"))
    CAMERA_FPS: int = int(os.getenv("CAMERA_FPS", "30"))
    CAMERA_BUFFER_SIZE: int = int(os.getenv("CAMERA_BUFFER_SIZE", "1"))
    CAMERA_RETRY_DELAY: int = int(os.getenv("CAMERA_RETRY_DELAY", "5"))
    CAMERA_THREADED: bool = os.getenv("CAMERA_THREADED", "True").lower() == "true"
    
    # Logging settings
    LOG_FILE: str = os.getenv("LOG_FILE", "/home/pi/logs/detections.log")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Image encoding settings
    JPEG_QUALITY: int = int(os.getenv("JPEG_QUALITY", "50"))
    
    # Twilio SMS Settings
    SMS_ENABLED: bool = os.getenv("SMS_ENABLED", "True").lower() == "true"
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_NUMBER: str = os.getenv("TWILIO_NUMBER", "")
    SMS_DESTINATION_NUMBER: str = os.getenv("SMS_DESTINATION_NUMBER", "")
    SMS_COOLDOWN_SECONDS: int = int(os.getenv("SMS_COOLDOWN_SECONDS", "60"))
    CALL_ENABLED: bool = os.getenv("CALL_ENABLED", "True").lower() == "true"
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing variables."""
        errors = []
        if not cls.API_KEY:
            errors.append("API_KEY is required")
        return errors


# Animal classification mappings
# Custom 5-Class Model: tiger, elephant, fox, monkey, wild_boar
PREDATOR_ANIMALS = {
    "tiger", "elephant", "fox", "monkey", "wild_boar"
}

SAFE_ANIMALS = {
    "cow", "sheep", "goat", "horse", "pig", "chicken", "bird", 
    "zebra", "giraffe"
}

# Priority mapping for predators (lower number = higher priority)
PREDATOR_PRIORITY = {
    # Priority 1 - Critical (Direct threat to human life)
    "tiger": 1,
    
    # Priority 2 - High (Dangerous large animals)
    "elephant": 2,
    "wild_boar": 2,
    
    # Priority 3 - Medium (Nuisance/Property threat)
    "monkey": 3,
    "fox": 3,
}

DEFAULT_PRIORITY = 4
