import cv2
import os
from ultralytics import YOLO

def detect_hazards(video_path, camera_id):
    # Load model
    model_path = "ml/weights/pothole_model.pt"
    if not os.path.exists(model_path):
        import urllib.request
        os.makedirs("ml/weights", exist_ok=True)
        urllib.request.urlretrieve("https://huggingface.co/Samdutse/pothole-yolov8/resolve/main/best.pt", model_path)
    model = YOLO(model_path)
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30
    
    hazards = []
    frame_number = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_number += 1
        # process 1 frame every 5 frames to speed up
        if frame_number % 5 != 0:
            continue
            
        results = model(frame, verbose=False)
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # get coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_idx = int(box.cls[0])
                cls_name = model.names[cls_idx] if model.names else "pothole"
                
                if conf > 0.25:
                    hazards.append({
                        "frame_number": frame_number,
                        "timestamp_sec": frame_number / fps,
                        "camera_id": camera_id,
                        "class_name": cls_name,
                        "confidence": conf,
                        "bbox": {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2
                        }
                    })
    
    cap.release()
    return hazards
