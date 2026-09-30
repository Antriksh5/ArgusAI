import os
import json
import collections
from app.ai.tracker import track_vehicles
from app.ai.plate_detector import detect_plates
from app.ai.ocr_reader import read_plate

def aggregate_plate_reads(video_path: str, camera_id: str):
    print("1. Running vehicle tracking...")
    tracked_vehicles = track_vehicles(video_path, camera_id)
    
    print("2. Running plate detection...")
    plate_detections, plate_dir = detect_plates(video_path, camera_id)
    
    vehicles_by_frame = collections.defaultdict(list)
    for v in tracked_vehicles:
        if "track_id" in v:
            vehicles_by_frame[v["frame_number"]].append(v)
            
    print("3. Running OCR and aggregating...")
    raw_readings_by_track = collections.defaultdict(list)
    
    all_track_ids = set(v["track_id"] for v in tracked_vehicles if "track_id" in v)
    
    for p in plate_detections:
        px1, py1, px2, py2 = p["bbox"]["x1"], p["bbox"]["y1"], p["bbox"]["x2"], p["bbox"]["y2"]
        cx, cy = (px1 + px2) / 2, (py1 + py2) / 2
        
        assigned_track_id = None
        for v in vehicles_by_frame.get(p["frame_number"], []):
            vx1, vy1, vx2, vy2 = v["bbox"]["x1"], v["bbox"]["y1"], v["bbox"]["x2"], v["bbox"]["y2"]
            # If the plate center is inside the vehicle bbox
            if vx1 <= cx <= vx2 and vy1 <= cy <= vy2:
                assigned_track_id = v["track_id"]
                break
                
        if assigned_track_id is None:
            continue
            
        crop_path = os.path.join(plate_dir, p.get("crop_filename", ""))
        if not os.path.exists(crop_path):
            continue
            
        ocr_out = read_plate(crop_path)
        
        if ocr_out["plate_text"]:
            reading = {
                "plate_text": ocr_out["plate_text"],
                "confidence": ocr_out["confidence"],
                "frame_number": p["frame_number"]
            }
            if reading not in raw_readings_by_track[assigned_track_id]:
                raw_readings_by_track[assigned_track_id].append(reading)
            
    # 4. Group by track_id and select best
    aggregated_results = []
    
    for track_id, readings in raw_readings_by_track.items():
        if not readings:
            continue
            
        # Highest confidence reading
        best_reading = max(readings, key=lambda x: x["confidence"])
        
        aggregated_results.append({
            "track_id": track_id,
            "camera_id": camera_id,
            "final_plate_text": best_reading["plate_text"],
            "final_confidence": round(best_reading["confidence"], 4),
            "num_readings_aggregated": len(readings),
            "all_raw_readings": readings
        })
        
    output_file = f"data/detections/aggregated_plates_{camera_id}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(aggregated_results, f, indent=2)
        
    print(f"Aggregation complete. Found {len(all_track_ids)} distinct vehicle tracks.")
    print(f"Tracks with at least one plate reading: {len(aggregated_results)}")
    print(f"Results saved to {output_file}")
    
    return aggregated_results, all_track_ids, output_file
