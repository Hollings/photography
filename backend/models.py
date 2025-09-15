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
    medium_url     = Column(String)
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
    # Feed/publication fields (nullable = not published)
    posted_at      = Column(DateTime, nullable=True)
    post_title     = Column(String, nullable=True)
    post_summary   = Column(String, nullable=True)

    # Expose a virtual taken_at field to API consumers. For new photos we set
    # created_at from EXIF DateTimeOriginal, so this returns that value. For
    # older photos (uploaded before the change) this will be the upload time
    # until a backfill is performed.
    @property
    def taken_at(self):  # type: ignore[override]
        return self.created_at

# Bootstrap tables (no‑op if already present)
Base.metadata.create_all(bind=engine)

# Lightweight migration: add medium_url column to existing SQLite DBs if missing
try:
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            rows = conn.exec_driver_sql("PRAGMA table_info(photos)").fetchall()
            cols = {row[1] for row in rows}
            if "medium_url" not in cols:
                conn.exec_driver_sql("ALTER TABLE photos ADD COLUMN medium_url TEXT")
            if "posted_at" not in cols:
                conn.exec_driver_sql("ALTER TABLE photos ADD COLUMN posted_at DATETIME")
            if "post_title" not in cols:
                conn.exec_driver_sql("ALTER TABLE photos ADD COLUMN post_title TEXT")
            if "post_summary" not in cols:
                conn.exec_driver_sql("ALTER TABLE photos ADD COLUMN post_summary TEXT")
except Exception as _e:  # non-fatal; logs handled at app level if needed
    pass
