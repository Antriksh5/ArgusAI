from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event import VehicleEvent, HazardEvent
import json
import os
from geoalchemy2.shape import to_shape
from shapely.geometry import Point

router = APIRouter()

def serialize_event(event: VehicleEvent):
    loc_dict = None
    if event.location is not None:
        try:
            pt = to_shape(event.location)
            loc_dict = {"latitude": pt.y, "longitude": pt.x}  # type: ignore[attr-defined]
        except Exception as e:
            print(f"[WARN] Could not parse location for vehicle event {event.id}: {e}")

    return {
        "id": event.id,
        "camera_id": event.camera_id,
        "source_video": event.source_video,
        "is_simulated_reuse": event.is_simulated_reuse,
        "track_id": event.track_id,
        "event_type": event.event_type,
        "plate_text": event.plate_text,
        "plate_format_valid": event.plate_format_valid,
        "low_quality": event.low_quality,
        "confidence": event.confidence,
        "num_readings_aggregated": event.num_readings_aggregated,
        "location": loc_dict,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "is_watchlist_match": event.is_watchlist_match,
        "raw_readings": event.raw_readings
    }

@router.get("/events")
def get_events(include_low_quality: bool = False, db: Session = Depends(get_db)):
    q = db.query(VehicleEvent)
    if not include_low_quality:
        q = q.filter(VehicleEvent.low_quality == False)
    events = q.all()
    return [serialize_event(e) for e in events]

@router.get("/alerts")
def get_alerts(include_low_quality: bool = False, db: Session = Depends(get_db)):
    q = db.query(VehicleEvent).filter(VehicleEvent.is_watchlist_match == True)
    if not include_low_quality:
        q = q.filter(VehicleEvent.low_quality == False)
    events = q.all()
    return [serialize_event(e) for e in events]

def serialize_hazard(event: HazardEvent):
    loc_dict = None
    if event.location is not None:
        try:
            pt = to_shape(event.location)
            loc_dict = {"latitude": pt.y, "longitude": pt.x}  # type: ignore[attr-defined]
        except Exception as e:
            print(f"[WARN] Could not parse location for hazard event {event.id}: {e}")
    return {
        "id": event.id,
        "camera_id": event.camera_id,
        "source_video": event.source_video,
        "is_simulated_reuse": event.is_simulated_reuse,
        "frame_number": event.frame_number,
        "class_name": event.class_name,
        "confidence": event.confidence,
        "bbox": event.bbox,
        "verification_status": event.verification_status,
        "location": loc_dict,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
    }

@router.get("/hazards")
def get_hazards(db: Session = Depends(get_db)):
    events = db.query(HazardEvent).all()
    return [serialize_hazard(e) for e in events]

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    cameras_count = 3
    if os.path.exists("data/cameras.json"):
        with open("data/cameras.json") as f:
            cameras_count = len(json.load(f))
    
    # Filter vehicles to match the default view (hide low quality)
    vehicle_count = db.query(VehicleEvent).filter(VehicleEvent.low_quality == False).count()
    alert_count = db.query(VehicleEvent).filter(VehicleEvent.is_watchlist_match == True, VehicleEvent.low_quality == False).count()
    hazard_count = db.query(HazardEvent).count()
    return {
        "cameras": cameras_count,
        "vehicle_events": vehicle_count,
        "watchlist_alerts": alert_count,
        "hazards": hazard_count
    }

@router.get("/trajectories")
def get_trajectories(db: Session = Depends(get_db)):
    events = db.query(VehicleEvent).filter(VehicleEvent.low_quality == False).order_by(VehicleEvent.timestamp).all()
    from collections import defaultdict
    plate_groups = defaultdict(list)
    for e in events:
        plate_groups[e.plate_text].append(e)
    
    trajectories = []
    for plate, evs in plate_groups.items():
        cams = set([e.camera_id for e in evs])
        if len(cams) >= 2:
            pts = []
            is_sim = any(e.is_simulated_reuse for e in evs)
            is_watch = any(e.is_watchlist_match for e in evs)
            for e in evs:
                lat = lon = None
                if e.location is not None:
                    try:
                        pt = to_shape(e.location)
                        lat, lon = pt.y, pt.x
                    except Exception:
                        pass
                pts.append({
                    "camera_id": e.camera_id,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "lat": lat,
                    "lon": lon,
                    "confidence": e.confidence
                })
            trajectories.append({
                "plate_text": plate,
                "is_watchlist_match": is_watch,
                "is_simulated_reuse": is_sim,
                "points": pts
            })
    return trajectories

@router.get("/demo/trajectory")
def get_demo_trajectory():
    return {
        "plate_text": "TS07JS9670",
        "is_watchlist_match": True,
        "is_simulated_reuse": False,
        "points": [
            {
                "camera_id": "cam_bus_01_hyderabad_north",
                "timestamp": "2026-09-28T10:00:15Z",
                "lat": 17.3870,
                "lon": 78.4880,
                "confidence": 0.95
            },
            {
                "camera_id": "cam_bus_02_hyderabad_south",
                "timestamp": "2026-09-28T10:15:30Z",
                "lat": 17.3795,
                "lon": 78.4820,
                "confidence": 0.88
            },
            {
                "camera_id": "cam_bus_03_hyderabad_east",
                "timestamp": "2026-09-28T10:30:45Z",
                "lat": 17.3842,
                "lon": 78.4908,
                "confidence": 0.91
            }
        ]
    }
