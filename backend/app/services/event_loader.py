import os
import json
import datetime
import sys
import re
import cv2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.db.database import SessionLocal
from app.models.event import VehicleEvent, HazardEvent
from app.services.watchlist import check_watchlist

def get_camera_config():
    with open("data/cameras.json", "r") as f:
        cams = json.load(f)
    return {c["camera_id"]: c for c in cams}

def get_interpolated_location(route, progress):
    """
    Interpolates along a multi-waypoint route.
    route: list of [lat, lon] pairs.
    progress: float 0.0–1.0 representing how far along the route we are.
    """
    progress = max(0.0, min(1.0, progress))
    if len(route) == 1:
        return route[0][0], route[0][1]

    # Compute cumulative distances (simple Euclidean in degree-space — fine for city scale)
    import math
    segment_lengths = []
    for i in range(len(route) - 1):
        dlat = route[i+1][0] - route[i][0]
        dlon = route[i+1][1] - route[i][1]
        segment_lengths.append(math.sqrt(dlat**2 + dlon**2))
    total_length = sum(segment_lengths)

    if total_length == 0:
        return route[0][0], route[0][1]

    target_dist = progress * total_length
    accumulated = 0.0
    for i, seg_len in enumerate(segment_lengths):
        if accumulated + seg_len >= target_dist or i == len(segment_lengths) - 1:
            # Interpolate within this segment
            remaining = target_dist - accumulated
            t = (remaining / seg_len) if seg_len > 0 else 0.0
            t = max(0.0, min(1.0, t))
            lat = route[i][0] + t * (route[i+1][0] - route[i][0])
            lon = route[i][1] + t * (route[i+1][1] - route[i][1])
            return lat, lon
        accumulated += seg_len

    return route[-1][0], route[-1][1]

def get_simulated_time(start_time_iso, timestamp_sec):
    start = datetime.datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
    # ensure it's timezone naive UTC for postgres
    start = start.replace(tzinfo=None)
    return start + datetime.timedelta(seconds=timestamp_sec)

def is_valid_plate(plate):
    pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"
    return bool(re.match(pattern, plate))

def load_events(json_path: str):
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    cam_configs = get_camera_config()
    db = SessionLocal()
    try:
        count = 0
        for item in data:
            cam_id = item.get("camera_id", "unknown")
            cam = cam_configs.get(cam_id)
            if not cam:
                continue
                
            cap = cv2.VideoCapture(cam["source_video"])
            total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            cap.release()
            
            # Use first reading's frame number for time/space mapping
            raws = item.get("all_raw_readings", [])
            frame_number = raws[0]["frame_number"] if raws else 0
            
            progress = frame_number / total_frames if total_frames > 0 else 0
            lat, lon = get_interpolated_location(cam["route"], progress)
            timestamp_sec = frame_number / fps
            sim_time = get_simulated_time(cam["sim_start_time"], timestamp_sec)
            
            plate_text = item.get("final_plate_text", "")
            confidence = item.get("final_confidence", 0.0)
            
            valid_format = is_valid_plate(plate_text)
            low_quality = (confidence < 0.3) or (len(plate_text) < 6) or (not valid_format)
            is_match = check_watchlist(plate_text)
            
            event = VehicleEvent(
                camera_id=cam_id,
                source_video=cam["source_video"],
                is_simulated_reuse=cam["is_simulated_reuse"],
                track_id=item.get("track_id", 0),
                event_type="plate_reading",
                plate_text=plate_text,
                plate_format_valid=valid_format,
                low_quality=low_quality,
                confidence=confidence,
                num_readings_aggregated=item.get("num_readings_aggregated", 0),
                location=f"SRID=4326;POINT({lon} {lat})",
                timestamp=sim_time,
                raw_readings=raws,
                is_watchlist_match=is_match
            )
            db.add(event)
            count += 1
            
        db.commit()
        print(f"Successfully loaded {count} vehicle events into the database.")
    except Exception as e:
        db.rollback()
        print(f"Error loading vehicle events: {e}")
    finally:
        db.close()

def _cluster_hazards_spatial(detections, radius_meters=15):
    """
    Cluster raw per-frame hazard detections into distinct sighting events based on location.
    """
    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    clusters = []
    for det in detections:
        # Only cluster if lat/lon is available
        if "lat" not in det or "lon" not in det:
            continue
            
        merged = False
        for cluster in clusters:
            rep = max(cluster, key=lambda x: x.get("confidence", 0))
            if haversine(det["lat"], det["lon"], rep["lat"], rep["lon"]) <= radius_meters:
                cluster.append(det)
                merged = True
                break
        if not merged:
            clusters.append([det])

    clustered = []
    for cluster in clusters:
        best = max(cluster, key=lambda x: x.get("confidence", 0))
        result = dict(best)
        result["frames_observed_count"] = len(cluster)
        clustered.append(result)

    return clustered


def load_hazards(json_path: str):
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return
        
    with open(json_path, 'r') as f:
        data = json.load(f)

    raw_count = len(data)
    cam_configs = get_camera_config()

    # Cache video metadata per camera so we don't re-open the video per detection
    cam_meta = {}
    for cam_id, cam in cam_configs.items():
        cap = cv2.VideoCapture(cam["source_video"])
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()
        cam_meta[cam_id] = {"total_frames": total_frames, "fps": fps}

    # Pre-calculate lat/lon and timestamp for all detections for spatial clustering
    for item in data:
        cam_id = item.get("camera_id", "unknown")
        cam = cam_configs.get(cam_id)
        if not cam:
            continue
        meta = cam_meta.get(cam_id, {"total_frames": 1, "fps": 30.0})
        frame_number = item.get("frame_number", 0)
        progress = frame_number / meta["total_frames"]
        lat, lon = get_interpolated_location(cam["route"], progress)
        timestamp_sec = frame_number / meta["fps"]
        sim_time = get_simulated_time(cam["sim_start_time"], timestamp_sec)
        
        item["lat"] = lat
        item["lon"] = lon
        item["sim_time"] = sim_time

    # ── Cluster near-duplicate detections before persisting ──────────────
    clustered = _cluster_hazards_spatial(data, radius_meters=15)
    clustered_count = len(clustered)
    print(f"  Hazard clustering (15m radius): {raw_count} raw detections → {clustered_count} distinct sightings")

    db = SessionLocal()
    try:
        count = 0
        for item in clustered:
            cam_id = item.get("camera_id", "unknown")
            cam = cam_configs.get(cam_id)
            if not cam:
                continue

            conf = item.get("confidence", 0.0)
            verif_status = "unverified" if conf < 0.5 else "candidate"

            event = HazardEvent(
                camera_id=cam_id,
                source_video=cam["source_video"],
                is_simulated_reuse=cam["is_simulated_reuse"],
                frame_number=item.get("frame_number", 0),
                class_name=item.get("class_name", "pothole"),
                confidence=conf,
                bbox=item.get("bbox", {}),
                verification_status=verif_status,
                location=f"SRID=4326;POINT({item['lon']} {item['lat']})",
                timestamp=item["sim_time"]
            )
            db.add(event)
            count += 1
            
        db.commit()
        print(f"  Successfully loaded {count} hazard sightings into the database.")
    except Exception as e:
        db.rollback()
        print(f"Error loading hazard events: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    load_events("data/detections/aggregated_plates.json")
