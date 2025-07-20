from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String

from database import Base, engine

class Photo(Base):
    __tablename__ = "photos"
    id             = Column(Integer, primary_key=True)
    name           = Column(String, unique=True, nullable=False)
    sha1           = Column(String(40), nullable=False)
    size           = Column(Integer, nullable=False)
    original_url   = Column(String, nullable=False)
    small_url      = Column(String)
    thumbnail_url  = Column(String)
    sort_order     = Column(Integer, default=0, nullable=False)
    title          = Column(String)
    camera         = Column(String)
    lens           = Column(String)
    iso            = Column(Integer)
    aperture       = Column(String)
    shutter_speed  = Column(String)
    focal_length   = Column(String)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

# Bootstrap tables (no‑op if already present)
Base.metadata.create_all(bind=engine)
