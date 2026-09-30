import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from geoalchemy2 import Geometry
from app.db.database import Base

class VehicleEvent(Base):
    __tablename__ = "vehicle_events"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True, nullable=False)
    source_video = Column(String)
    is_simulated_reuse = Column(Boolean, default=False)
    track_id = Column(Integer, index=True, nullable=False)
    event_type = Column(String, default="plate_reading")
    plate_text = Column(String, index=True)
    plate_format_valid = Column(Boolean, default=False)
    low_quality = Column(Boolean, default=False)
    confidence = Column(Float)
    num_readings_aggregated = Column(Integer)
    # Using SRID 4326 (WGS 84 GPS coordinates)
    location = Column(Geometry('POINT', srid=4326))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    raw_readings = Column(JSON)
    is_watchlist_match = Column(Boolean, default=False)

class HazardEvent(Base):
    __tablename__ = "hazard_events"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True, nullable=False)
    source_video = Column(String)
    is_simulated_reuse = Column(Boolean, default=False)
    frame_number = Column(Integer)
    class_name = Column(String, default="pothole")
    confidence = Column(Float)
    bbox = Column(JSON)
    verification_status = Column(String)
    # Using SRID 4326 (WGS 84 GPS coordinates)
    location = Column(Geometry('POINT', srid=4326))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
