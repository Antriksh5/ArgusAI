import sys
import os
import json
import glob

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.services.plate_aggregator import aggregate_plate_reads
from app.services.event_loader import load_events, load_hazards
from app.ai.hazard_detector import detect_hazards
from app.db.database import Base, engine, SessionLocal
from app.models.event import VehicleEvent, HazardEvent

# Ensure DB tables exist
Base.metadata.create_all(bind=engine)

# ── Truncate both tables before a full reseed ─────────────────────────────
print("Truncating vehicle_events and hazard_events tables...")
db = SessionLocal()
try:
    db.query(HazardEvent).delete()
    db.query(VehicleEvent).delete()
    db.commit()
    print("Tables truncated.\n")
except Exception as e:
    db.rollback()
    print(f"Error truncating tables: {e}")
finally:
    db.close()

with open("data/cameras.json", "r") as f:
    cameras = json.load(f)

for cam in cameras:
    camera_id = cam["camera_id"]
    video_path = cam["source_video"]
    print(f"==================================================")
    print(f"Processing {video_path} for {camera_id}")
    print(f"==================================================")

    # ── Vehicle + Plate Detection ─────────────────────────────────────────
    if cam.get("purpose") != "hazard":
        print(f"Running vehicle tracking & plate detection for {camera_id}...")
        _, _, plate_output_file = aggregate_plate_reads(video_path, camera_id)
        load_events(plate_output_file)
    else:
        print(f"Skipping ALPR for {camera_id} (purpose: hazard)")

    # ── Hazard Detection ──────────────────────────────────────────────────
    if cam.get("purpose") != "alpr":
        print(f"4. Running hazard detection...")
        hazards = detect_hazards(video_path, camera_id)

        hazard_file = f"data/detections/hazards_{camera_id}.json"
        os.makedirs(os.path.dirname(hazard_file), exist_ok=True)
        with open(hazard_file, 'w') as f:
            json.dump(hazards, f)

        print(f"Found {len(hazards)} raw hazard detections. Loading to DB...")
        load_hazards(hazard_file)
    else:
        print(f"Skipping hazard detection for {camera_id} (purpose: alpr)")

    print(f"Done processing for {camera_id}\n")

# ── Final row-count report ────────────────────────────────────────────────
print("=" * 60)
print("PIPELINE COMPLETE — DATABASE ROW COUNTS")
print("=" * 60)
db = SessionLocal()
try:
    total_v = db.query(VehicleEvent).count()
    total_h = db.query(HazardEvent).count()
    print(f"VehicleEvent total: {total_v}")
    print(f"HazardEvent  total: {total_h}")
    print()
    for cam in cameras:
        cid = cam["camera_id"]
        v_count = db.query(VehicleEvent).filter(VehicleEvent.camera_id == cid).count()
        h_count = db.query(HazardEvent).filter(HazardEvent.camera_id == cid).count()
        print(f"  {cid}: {v_count} vehicle events, {h_count} hazard events")
finally:
    db.close()
print("=" * 60)
