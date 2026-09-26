import os
import cv2
from .vehicle_detector import detect_vehicles
from ultralytics import YOLO

# Minimum pixel area for a plate crop to be considered valid.
# Very small crops are almost certainly clipped or degenerate.
MIN_CROP_AREA_PX = 100  # ~10x10 px minimum

# Classes that are buses / large vehicles — their "lower third" is useless
# because the plate is at bumper height, not mid-vehicle.
# COCO class IDs: 5 = bus, 7 = truck
LARGE_VEHICLE_CLASS_IDS = {5, 7}

# ── YOLOv8 License Plate Detector ──────────────────────────────────────────
_plate_model = None

def _get_plate_model():
    global _plate_model
    if _plate_model is None:
        model_path = os.path.abspath("ml/weights/yolov8_plate_detector.pt")
        _plate_model = YOLO(model_path)
    return _plate_model

def detect_plates(video_path: str, camera_id: str) -> list[dict]:
    """
    Runs license plate detection on a video file using a pretrained YOLOv8 model.
    """
    detections = []
    
    vehicle_detections = detect_vehicles(video_path, camera_id)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    plate_dir = "data/detections/plates"
    os.makedirs(plate_dir, exist_ok=True)

    model = _get_plate_model()
    
    frames_dict: dict[int, list[dict]] = {}
    for det in vehicle_detections:
        fn = det["frame_number"]
        if fn not in frames_dict:
            frames_dict[fn] = []
        frames_dict[fn].append(det)

    frame_count = 0
    saved = 0
    skipped_small = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        
        # We process every frame that has a vehicle detection to save time
        if frame_count not in frames_dict:
            continue

        height, width = frame.shape[:2]

        for i, v_det in enumerate(frames_dict[frame_count]):
            v_box = v_det["bbox"]
            v_x1, v_y1, v_x2, v_y2 = int(v_box["x1"]), int(v_box["y1"]), int(v_box["x2"]), int(v_box["y2"])
            v_x1 = max(0, min(width, v_x1))
            v_y1 = max(0, min(height, v_y1))
            v_x2 = max(0, min(width, v_x2))
            v_y2 = max(0, min(height, v_y2))
            
            if v_x2 <= v_x1 or v_y2 <= v_y1:
                continue

            vehicle_crop = frame[v_y1:v_y2, v_x1:v_x2]
            
            # Run plate detection ONLY on the cropped vehicle image
            results = model(vehicle_crop, verbose=False, imgsz=640, conf=0.05)
            
            for j, box in enumerate(results[0].boxes):
                px1, py1, px2, py2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                
                # Convert back to full-frame coordinates
                p_x1 = int(max(0, min(vehicle_crop.shape[1], px1))) + v_x1
                p_y1 = int(max(0, min(vehicle_crop.shape[0], py1))) + v_y1
                p_x2 = int(max(0, min(vehicle_crop.shape[1], px2))) + v_x1
                p_y2 = int(max(0, min(vehicle_crop.shape[0], py2))) + v_y1
                
                plate_crop = frame[p_y1:p_y2, p_x1:p_x2]
                
                area = plate_crop.shape[0] * plate_crop.shape[1] if plate_crop.size > 0 else 0
                if area < MIN_CROP_AREA_PX:
                    skipped_small += 1
                    continue
                    
                crop_filename = f"v3_{camera_id}_{frame_count}_{i}_{j}.jpg"
                crop_path = os.path.join(plate_dir, crop_filename)
                cv2.imwrite(crop_path, plate_crop)
                saved += 1
                
                detections.append({
                    "frame_number": frame_count,
                    "timestamp_sec": v_det["timestamp_sec"],
                    "camera_id": camera_id,
                    "class_name": "license_plate",
                    "confidence": round(conf, 4),
                    "bbox": {
                        "x1": round(float(p_x1), 2),
                        "y1": round(float(p_y1), 2),
                        "x2": round(float(p_x2), 2),
                        "y2": round(float(p_y2), 2),
                    },
                })

    cap.release()
    print(f"[plate_detector] saved={saved}, skipped_small={skipped_small}")
    return detections


def _plate_bbox_from_vehicle(v_box: dict, class_id: int) -> tuple[int, int, int, int]:
    """
    Given a vehicle bounding box, return (x1, y1, x2, y2) for the candidate
    plate region using a smarter heuristic than a flat lower-third cut.
    """
    x1, y1, x2, y2 = v_box["x1"], v_box["y1"], v_box["x2"], v_box["y2"]
    w = x2 - x1
    h = y2 - y1

    if class_id in LARGE_VEHICLE_CLASS_IDS:
        frac_top = 0.90
        frac_w   = 0.35
    else:
        frac_top = 0.78
        frac_w   = 0.65

    cx = (x1 + x2) / 2
    pw = w * frac_w
    p_x1 = cx - pw / 2
    p_x2 = cx + pw / 2
    p_y1 = y1 + h * frac_top
    p_y2 = y2

    return int(p_x1), int(p_y1), int(p_x2), int(p_y2)


def detect_plates_heuristic_fallback(video_path: str, camera_id: str) -> list[dict]:
    """
    FALLBACK ONLY: Runs license plate detection on a video file.

    NOTE: Uses a heuristic fallback — runs vehicle detector first and crops
    the estimated plate region from each vehicle bbox.  The crop position is
    class-aware (cars vs buses/trucks) to reduce garbage crops.
    """
    detections = []

    vehicle_detections = detect_vehicles(video_path, camera_id)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    plate_dir = "data/detections/plates"
    os.makedirs(plate_dir, exist_ok=True)

    frames_dict: dict[int, list[dict]] = {}
    for det in vehicle_detections:
        fn = det["frame_number"]
        if fn not in frames_dict:
            frames_dict[fn] = []
        frames_dict[fn].append(det)

    frame_count = 0
    saved = 0
    skipped_small = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        if frame_count not in frames_dict:
            continue

        height, width = frame.shape[:2]

        for i, v_det in enumerate(frames_dict[frame_count]):
            v_box = v_det["bbox"]

            class_name = v_det.get("class_name", "car")
            coco_id = {"car": 2, "motorcycle": 3, "bus": 5, "truck": 7}.get(class_name, 2)

            p_x1, p_y1, p_x2, p_y2 = _plate_bbox_from_vehicle(v_box, coco_id)

            p_x1 = max(0, min(width, p_x1))
            p_x2 = max(0, min(width, p_x2))
            p_y1 = max(0, min(height, p_y1))
            p_y2 = max(0, min(height, p_y2))

            plate_crop = frame[p_y1:p_y2, p_x1:p_x2]

            area = plate_crop.shape[0] * plate_crop.shape[1] if plate_crop.size > 0 else 0
            if area < MIN_CROP_AREA_PX:
                skipped_small += 1
                continue

            crop_filename = f"{camera_id}_{frame_count}_{i}.jpg"
            crop_path = os.path.join(plate_dir, crop_filename)
            cv2.imwrite(crop_path, plate_crop)
            saved += 1

            detections.append({
                "frame_number": frame_count,
                "timestamp_sec": v_det["timestamp_sec"],
                "camera_id": camera_id,
                "class_name": "license_plate",
                "confidence": v_det["confidence"],
                "bbox": {
                    "x1": round(float(p_x1), 2),
                    "y1": round(float(p_y1), 2),
                    "x2": round(float(p_x2), 2),
                    "y2": round(float(p_y2), 2),
                },
            })

    cap.release()
    print(f"[plate_detector fallback] saved={saved}, skipped_small={skipped_small}")
    return detections
