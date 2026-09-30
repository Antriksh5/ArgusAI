import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.db.database import SessionLocal
from app.models.event import VehicleEvent, HazardEvent
from app.services.event_loader import load_hazards

def run():
    db = SessionLocal()
    
    print("1. Removing invalid rows based on new camera purposes...")
    
    # Remove vehicles from hazard camera (cam_bus_03)
    deleted_vehicles = db.query(VehicleEvent).filter(VehicleEvent.camera_id == "cam_bus_03_hyderabad_east").delete()
    print(f"Deleted {deleted_vehicles} noisy VehicleEvent rows from cam_bus_03_hyderabad_east")
    
    # Remove hazards from ALPR cameras (cam_bus_01, cam_bus_02)
    deleted_hazards = db.query(HazardEvent).filter(HazardEvent.camera_id.in_(["cam_bus_01_hyderabad_north", "cam_bus_02_hyderabad_south"])).delete()
    print(f"Deleted {deleted_hazards} HazardEvent rows from ALPR cameras")
    
    # Delete the remaining old hazards to re-cluster them
    deleted_old_hazards = db.query(HazardEvent).delete()
    print(f"Deleted {deleted_old_hazards} old HazardEvent rows before spatial clustering")
    
    db.commit()
    db.close()
    
    print("\n2. Reloading hazards using new 15m spatial clustering...")
    load_hazards("data/detections/hazards_cam_bus_03_hyderabad_east.json")
    
    db = SessionLocal()
    print("\n3. Final Row Counts:")
    for cam_id in ["cam_bus_01_hyderabad_north", "cam_bus_02_hyderabad_south", "cam_bus_03_hyderabad_east"]:
        v = db.query(VehicleEvent).filter(VehicleEvent.camera_id == cam_id).count()
        h = db.query(HazardEvent).filter(HazardEvent.camera_id == cam_id).count()
        print(f"  {cam_id}: {v} vehicles, {h} hazards")
        
if __name__ == '__main__':
    run()
