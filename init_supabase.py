import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.db.database import engine, Base
from app.services.event_loader import load_events, load_hazards

print("Enabling PostGIS extension...")
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    conn.commit()

print("Creating tables in Supabase...")
Base.metadata.create_all(bind=engine)

from app.db.database import SessionLocal
from app.models.event import VehicleEvent, HazardEvent

db = SessionLocal()
print("Clearing existing data...")
db.query(HazardEvent).delete()
db.query(VehicleEvent).delete()
db.commit()
db.close()

print("Loading vehicle events from ALPR cameras (cam01, cam02 only)...")
load_events("data/detections/aggregated_plates_cam_bus_01_hyderabad_north.json")
load_events("data/detections/aggregated_plates_cam_bus_02_hyderabad_south.json")

print("Loading hazard events from hazard camera (cam03 only)...")
load_hazards("data/detections/hazards_cam_bus_03_hyderabad_east.json")

db = SessionLocal()
print("\nInitialization complete! Supabase counts:")
for cam_id in ["cam_bus_01_hyderabad_north", "cam_bus_02_hyderabad_south", "cam_bus_03_hyderabad_east"]:
    v = db.query(VehicleEvent).filter(VehicleEvent.camera_id == cam_id).count()
    h = db.query(HazardEvent).filter(HazardEvent.camera_id == cam_id).count()
    print(f"  {cam_id}: {v} vehicles, {h} hazards")
db.close()
