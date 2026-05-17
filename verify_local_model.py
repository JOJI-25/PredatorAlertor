"""
Verify Local YOLO Model
This script attempts to load the local model and run inference.
"""
import os
import cv2
import sys
import numpy as np
from detector import WildlifeDetector
from config import Config

def main():
    print("--- Verifying Local YOLO Model ---")
    
    model_path = Config.MODEL_PATH
    print(f"Model Path: {model_path}")
    
    if not os.path.exists(model_path):
        print(f"[ERROR] Model file not found at: {model_path}")
        return

    # Initialize detector
    print("Initializing detector (this may take a moment)...")
    detector = WildlifeDetector()
    if not detector.initialize():
        print("[ERROR] Failed to initialize detector.")
        return
        
    print("[SUCCESS] Detector initialized.")
        
    # Create dummy image
    print("Running inference on dummy image...")
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    
    start_time = os.times()[4]
    detections = detector.detect(frame)
    end_time = os.times()[4]
    
    duration = end_time - start_time
    
    print(f"Inference completed in {duration:.4f} seconds.")
    print(f"Detections: {len(detections)}")
    
    print("\n[SUCCESS] Local model is working correctly!")

if __name__ == "__main__":
    main()
