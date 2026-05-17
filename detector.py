"""
PredatorAlert Detection Module
Runs wildlife detection using YOLO model (PyTorch .pt or optimized ONNX) for Raspberry Pi 5.
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional, List
from ultralytics import YOLO
from config import Config
from logger import detection_logger


@dataclass
class Detection:
    """Represents a single detection result."""
    class_name: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    
    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Return bounding box as (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)


class WildlifeDetector:
    """Wildlife detection using YOLO model (.pt or .onnx) for Raspberry Pi 5."""
    
    def __init__(self):
        self.model = None
        self._initialized = False
        self.model_path = Config.MODEL_PATH
        self.imgsz = Config.INFERENCE_IMGSZ
    
    def initialize(self) -> bool:
        """
        Initialize YOLO model for Raspberry Pi 5 (PyTorch or ONNX).
        Returns True if successful.
        """
        try:
            detection_logger.log_api_status(
                "Loading YOLO model...",
                f"path={self.model_path} | imgsz={self.imgsz}"
            )
            
            # Load YOLO model - Ultralytics handles .pt files natively
            self.model = YOLO(self.model_path, task='detect')
            
            # Warm up with dummy inference
            dummy_frame = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
            self.model(dummy_frame, verbose=False, imgsz=self.imgsz)
            
            detection_logger.log_api_status(
                "YOLO model loaded successfully",
                f"classes={list(self.model.names.values())}"
            )
            
            self._initialized = True
            return True
            
        except Exception as e:
            detection_logger.log_error(f"Failed to load YOLO model from {self.model_path}", e)
            return False
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run YOLO detection on a frame.
        Returns list of Detection objects above confidence threshold.
        """
        if not self._initialized or self.model is None:
            detection_logger.log_error("Detector not initialized")
            return []
        
        try:
            # Run YOLO inference
            results = self.model(
                frame, 
                conf=Config.CONFIDENCE_THRESHOLD, 
                verbose=False,
                imgsz=self.imgsz  # Use configured image size for faster inference
            )
            
            detections = []
            
            # Parse predictions
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    # Get class ID and name
                    cls_id = int(box.cls[0])
                    class_name = self.model.names[cls_id]
                    
                    # Normalize class name
                    class_name = class_name.lower().replace(" ", "_").replace("-", "_")
                    
                    # Get coordinates (xywh format: center x, y, width, height)
                    x, y, w, h = box.xywh[0].tolist()
                    
                    detection = Detection(
                        class_name=class_name,
                        confidence=float(box.conf[0]),
                        x=int(x),
                        y=int(y),
                        width=int(w),
                        height=int(h)
                    )
                    
                    detections.append(detection)
            
            return detections
            
        except Exception as e:
            detection_logger.log_error("YOLO inference failed", e)
            return []
    
    def is_ready(self) -> bool:
        """Check if detector is initialized and ready."""
        return self._initialized and self.model is not None
