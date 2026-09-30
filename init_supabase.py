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

print("Loading vehicle events...")
# This will load vehicles based on cameras.json (which skips cam03 because it's hazard-only in our manual code? Actually load_events just uses whatever is in aggregated_plates.json. We can run it and then delete the cam03 ones like we did before)
load_events("data/detections/aggregated_plates.json")

print("Loading hazard events...")
load_hazards("data/detections/hazards_cam_bus_03_hyderabad_east.json")

from app.db.database import SessionLocal
from app.models.event import VehicleEvent, HazardEvent

db = SessionLocal()
print("Cleaning up noisy ALPR events from hazard camera...")
db.query(VehicleEvent).filter(VehicleEvent.camera_id == "cam_bus_03_hyderabad_east").delete()
db.commit()

print("Initialization complete! Supabase counts:")
for cam_id in ["cam_bus_01_hyderabad_north", "cam_bus_02_hyderabad_south", "cam_bus_03_hyderabad_east"]:
    v = db.query(VehicleEvent).filter(VehicleEvent.camera_id == cam_id).count()
    h = db.query(HazardEvent).filter(HazardEvent.camera_id == cam_id).count()
    print(f"  {cam_id}: {v} vehicles, {h} hazards")
db.close()
