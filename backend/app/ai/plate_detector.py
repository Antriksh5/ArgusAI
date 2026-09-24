import os
import cv2
from .vehicle_detector import detect_vehicles

# Minimum pixel area for a plate crop to be considered valid.
# Very small crops are almost certainly clipped or degenerate.
MIN_CROP_AREA_PX = 800  # ~40x20 px minimum

# Classes that are buses / large vehicles — their "lower third" is useless
# because the plate is at bumper height, not mid-vehicle.
# COCO class IDs: 5 = bus, 7 = truck
LARGE_VEHICLE_CLASS_IDS = {5, 7}

def _plate_bbox_from_vehicle(v_box: dict, class_id: int) -> tuple[int, int, int, int]:
    """
    Given a vehicle bounding box, return (x1, y1, x2, y2) for the candidate
    plate region using a smarter heuristic than a flat lower-third cut.

    Strategy:
    - For cars / motorcycles (small vehicles): plate is in the bottom ~20% of
      the vehicle bbox, horizontally centred and narrowed to ~60% of vehicle width.
    - For buses / trucks: plate is in the very bottom ~10% and the horizontal
      extent is narrowed significantly (plates are much narrower than the vehicle).
    """
    x1, y1, x2, y2 = v_box["x1"], v_box["y1"], v_box["x2"], v_box["y2"]
    w = x2 - x1
    h = y2 - y1

    if class_id in LARGE_VEHICLE_CLASS_IDS:
        # Buses / trucks: plate is at the very bottom, narrow band
        frac_top = 0.90     # start at 90% of height
        frac_w   = 0.35     # only 35% of vehicle width, centred
    else:
        # Cars / motorcycles: bottom 20%, slightly narrowed
        frac_top = 0.78     # start at 78% of height
        frac_w   = 0.65     # 65% of vehicle width, centred

    cx = (x1 + x2) / 2
    pw = w * frac_w
    p_x1 = cx - pw / 2
    p_x2 = cx + pw / 2
    p_y1 = y1 + h * frac_top
    p_y2 = y2

    return int(p_x1), int(p_y1), int(p_x2), int(p_y2)


def detect_plates(video_path: str, camera_id: str) -> list[dict]:
    """
    Runs license plate detection on a video file.

    NOTE: Uses a heuristic fallback — runs vehicle detector first and crops
    the estimated plate region from each vehicle bbox.  The crop position is
    class-aware (cars vs buses/trucks) to reduce garbage crops.

    This is a placeholder to replace once we fine-tune a real plate detector.

    Returns a list of structured detection events for license plates.
    """
    detections = []

    # Run vehicle detection first to get bounding boxes
    vehicle_detections = detect_vehicles(video_path, camera_id)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    plate_dir = "data/detections/plates"
    os.makedirs(plate_dir, exist_ok=True)

    # Group vehicle detections by frame to avoid reading frames multiple times
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

            # Map class name back to COCO id for the heuristic
            class_name = v_det.get("class_name", "car")
            # COCO: car=2, motorcycle=3, bus=5, truck=7
            coco_id = {"car": 2, "motorcycle": 3, "bus": 5, "truck": 7}.get(class_name, 2)

            p_x1, p_y1, p_x2, p_y2 = _plate_bbox_from_vehicle(v_box, coco_id)

            # Clamp to frame
            p_x1 = max(0, min(width, p_x1))
            p_x2 = max(0, min(width, p_x2))
            p_y1 = max(0, min(height, p_y1))
            p_y2 = max(0, min(height, p_y2))

            plate_crop = frame[p_y1:p_y2, p_x1:p_x2]

            # Skip degenerate / invisible crops
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
    print(f"[plate_detector] saved={saved}, skipped_small={skipped_small}")
    return detections
