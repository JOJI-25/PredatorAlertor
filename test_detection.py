import cv2
import sys
from detector import WildlifeDetector
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_detection():
    import os
    import glob

    image_path = None

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Prompt user for input
        print("Enter the path to your image file (or press Enter to auto-detect):")
        user_input = input(">> ").strip()
        
        if user_input:
            # Remove quotes if user pasted path with quotes
            image_path = user_input.replace('"', '').replace("'", "")
        else:
            # Find the most recently modified jpg file in the current directory
            jpg_files = glob.glob("*.jpg") + glob.glob("*.jpeg") + glob.glob("*.png")
            if jpg_files:
                image_path = max(jpg_files, key=os.path.getmtime)
                print(f"No path provided. Using most recent image: {image_path}")
            else:
                image_path = "test_bear.jpg"
                print(f"No images found. Defaulting to: {image_path}")

    print(f"Testing detection on {image_path}...")
    
    # Initialize detector
    detector = WildlifeDetector()
    if not detector.initialize():
        print("Failed to initialize detector")
        sys.exit(1)
        
    # Load image
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"Failed to load image: {image_path}")
        sys.exit(1)
        
    # Run detection
    detections = detector.detect(frame)
    
    # Print results
    print(f"\n--- Detection Results ({len(detections)}) ---")
    for d in detections:
        print(f"Animal: {d.class_name}, Confidence: {d.confidence:.2f}, Box: {d.bbox}")
        
    if not detections:
        print("No animals detected.")

if __name__ == "__main__":
    test_detection()
