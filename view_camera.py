import cv2
import time
import sys
from camera import Camera
from detector import WildlifeDetector
from config import Config

def main():
    print("Initializing Camera and Detector...")
    
    # Initialize components
    camera = Camera()
    detector = WildlifeDetector()
    
    if not camera.connect():
        print("Error: Could not connect to camera.")
        return

    if not detector.initialize():
        print("Error: Could not initialize detector.")
        return

    print("Starting video feed. Press 'q' to exit.")

    try:
        while True:
            # Capture frame
            frame = camera.capture_frame()
            if frame is None:
                continue

            # Run detection
            detections = detector.detect(frame)

            # Draw detections
            for d in detections:
                # bounding box
                cv2.rectangle(frame, (d.x - d.width//2, d.y - d.height//2), 
                            (d.x + d.width//2, d.y + d.height//2), (0, 255, 0), 2)
                
                # label
                label = f"{d.class_name} {d.confidence:.2f}"
                cv2.putText(frame, label, (d.x - d.width//2, d.y - d.height//2 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Show frame
            cv2.imshow("PredatorAlert View - Press 'q' to quit", frame)

            # Exit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        camera.disconnect()
        cv2.destroyAllWindows()
        print("Stopped.")

if __name__ == "__main__":
    main()
