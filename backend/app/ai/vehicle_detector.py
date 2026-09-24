import cv2
from ultralytics import YOLO

def detect_vehicles(video_path: str, camera_id: str) -> list[dict]:
    """
    Runs vehicle detection on a video file.
    Returns a list of structured detection events.
    """
    model = YOLO("yolov8n.pt") 
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps != fps:  # handle division by zero or NaN
        fps = 30.0

    detections = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        timestamp_sec = frame_count / fps
        
        # Run inference, ignoring ultralytics verbose logging
        # Classes: 2 (car), 3 (motorcycle), 5 (bus), 7 (truck)
        results = model(frame, verbose=False, classes=[2, 3, 5, 7]) 
        result = results[0]
        boxes = result.boxes
        
        for box in boxes:
            b = box.xyxy[0].tolist()
            cls = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            class_name = model.names[cls]
            
            detections.append({
                "frame_number": frame_count,
                "timestamp_sec": round(timestamp_sec, 3),
                "camera_id": camera_id,
                "class_name": class_name,
                "confidence": round(conf, 4),
                "bbox": {
                    "x1": round(b[0], 2),
                    "y1": round(b[1], 2),
                    "x2": round(b[2], 2),
                    "y2": round(b[3], 2)
                }
            })

    cap.release()
    return detections
