import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

# Default to a local argus_db if not provided
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://argus_app:@localhost:5432/argus_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
