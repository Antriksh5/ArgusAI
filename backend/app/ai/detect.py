import cv2
from ultralytics import YOLO
import sys

def run_detection(video_path):
    print(f"Loading YOLOv8 model for vehicle detection on {video_path}...")
    # Load the pretrained YOLOv8n (nano) model - CPU default unless GPU is available
    model = YOLO("yolov8n.pt") 
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        sys.exit(1)

    frame_count = 0
    print("Starting frame processing...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        # Run inference, ignoring ultralytics verbose logging
        # Classes: 2 (car), 3 (motorcycle), 5 (bus), 7 (truck) in COCO
        results = model(frame, verbose=False, classes=[2, 3, 5, 7]) 

        result = results[0]
        boxes = result.boxes
        
        if len(boxes) > 0:
            print(f"\n--- Frame {frame_count} ---")
            for box in boxes:
                # get coordinates (x1, y1, x2, y2), class id, and confidence
                b = box.xyxy[0].tolist()
                cls = int(box.cls[0].item())
                conf = box.conf[0].item()
                class_name = model.names[cls]
                
                print(f"Detected {class_name} at [x1:{b[0]:.1f}, y1:{b[1]:.1f}, x2:{b[2]:.1f}, y2:{b[3]:.1f}] with confidence {conf:.2f}")

        # Limit to 30 frames for the test script
        if frame_count >= 30:
            print("Reached 30 frames test limit, stopping.")
            break

    cap.release()
    print("\nFinished processing.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python detect.py <path_to_video>")
        sys.exit(1)
    run_detection(sys.argv[1])
