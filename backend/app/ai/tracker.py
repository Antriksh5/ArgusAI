import cv2
from .vehicle_detector import get_vehicle_model, parse_vehicle_results

def track_vehicles(video_path: str, camera_id: str) -> list[dict]:
    """
    Runs vehicle detection and tracking on a video file.
    Returns a list of structured detection events, including track_id.
    """
    model = get_vehicle_model()
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps != fps:
        fps = 30.0

    detections = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        timestamp_sec = frame_count / fps
        
        # Use model.track to apply ByteTrack over the detections
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False, classes=[2, 3, 5, 7])
        
        # Parse using the shared logic which extracts .id into track_id
        frame_detections = parse_vehicle_results(results, frame_count, timestamp_sec, camera_id)
        detections.extend(frame_detections)

    cap.release()
    return detections
