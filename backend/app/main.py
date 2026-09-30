from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import events
from app.db.database import engine, Base
from sqlalchemy import text

# Ensure PostGIS is enabled before creating tables
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    conn.commit()

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)
app = FastAPI(title="ArgusAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "ArgusAI API is running"}
