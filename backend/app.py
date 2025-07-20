#!/usr/bin/env python3
"""
REST‑based photo‑hosting service.

  • Uploads original images plus “small” (≤ 1600 px) and “thumbnail”
    (≤ 400 px) variants to an S3 bucket.
  • Extracts EXIF / XMP metadata (camera, lens, ISO, aperture, shutter,
    focal length, title, rating); callers may override *title* / *rating*
    in the request.
  • Stores all metadata and S3 URLs in a relational database.
  • Exposes a small FastAPI surface:

      GET    /photos           → list all records
      POST   /photos           → upload new image
      DELETE /photos/{id}      → remove image and variants
"""

import hashlib
import logging
import mimetypes
import os
import tempfile
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterator

import boto3
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, ImageOps, ExifTags
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ── Configuration ──────────────────────────────────────────────────────────
load_dotenv()

AWS_REGION   = os.getenv("AWS_DEFAULT_REGION", "us‑east‑1")
S3_BUCKET    = os.getenv("S3_BUCKET")
AWS_KEY      = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET   = os.getenv("AWS_SECRET_ACCESS_KEY")
DB_URL       = os.getenv("DATABASE_URL", "sqlite:///photos.db")
LOG_LEVEL    = os.getenv("LOG_LEVEL", "INFO").upper()

if not all([S3_BUCKET, AWS_KEY, AWS_SECRET]):
    raise RuntimeError("S3_BUCKET / AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are required")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y‑%m‑%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET,
)

engine        = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal  = sessionmaker(bind=engine, expire_on_commit=False)
Base          = declarative_base()

# ── ORM model ──────────────────────────────────────────────────────────────
class Photo(Base):
    __tablename__ = "photos"

    id             = Column(Integer, primary_key=True)
    name           = Column(String, unique=True, nullable=False)
    sha1           = Column(String(40), nullable=False)
    size           = Column(Integer, nullable=False)
    original_url   = Column(String, nullable=False)
    small_url      = Column(String)
    thumbnail_url  = Column(String)
    rating         = Column(Integer)
    title          = Column(String)
    camera         = Column(String)
    lens           = Column(String)
    iso            = Column(Integer)
    aperture       = Column(String)
    shutter_speed  = Column(String)
    focal_length   = Column(String)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)


Base.metadata.create_all(bind=engine)

# ── Utility helpers ────────────────────────────────────────────────────────
def db_session() -> Iterator[Session]:
    """FastAPI dependency providing a SQLAlchemy Session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def file_sha1(fp: Path) -> str:
    h = hashlib.sha1()
    with fp.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def public_url(key: str) -> str:
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


def upload_file(path: Path, key: str) -> str:
    mimetype, _ = mimetypes.guess_type(path.name)
    logger.info("Uploading %s → %s", path.name, key)
    s3.upload_file(
        str(path),
        S3_BUCKET,
        key,
        ExtraArgs={"ACL": "public-read", "ContentType": mimetype or "application/octet-stream"},
    )
    return public_url(key)


def delete_file(key: str) -> None:
    logger.info("Deleting key=%s from S3", key)
    s3.delete_object(Bucket=S3_BUCKET, Key=key)


# ── EXIF extraction ────────────────────────────────────────────────────────
def _rational_to_float(value) -> float | None:
    if isinstance(value, (tuple, list)) and len(value) == 2 and value[1]:
        return value[0] / value[1]
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def extract_exif(path: Path) -> dict[str, Any]:
    exif: dict[str, Any] = {}
    try:
        with Image.open(path) as img:
            raw_exif = img._getexif() or {}
    except Exception:
        return exif

    tag_map = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}

    if (model := tag_map.get("Model")):
        exif["camera"] = str(model).strip()

    if (lens := tag_map.get("LensModel")):
        exif["lens"] = str(lens).strip()

    if (iso_val := tag_map.get("ISOSpeedRatings") or tag_map.get("PhotographicSensitivity")):
        exif["iso"] = int(iso_val[0] if isinstance(iso_val, (list, tuple)) else iso_val)

    if (fnum := tag_map.get("FNumber")) is not None:
        if (f := _rational_to_float(fnum)):
            exif["aperture"] = f"f/{f:.1f}"

    if (shutter := tag_map.get("ExposureTime")) is not None:
        if isinstance(shutter, (tuple, list)) and len(shutter) == 2 and shutter[1]:
            exif["shutter_speed"] = f"{shutter[0]}/{shutter[1]} s"
        else:
            exif["shutter_speed"] = str(shutter)

    if (focal := tag_map.get("FocalLength")) is not None:
        if (fl := _rational_to_float(focal)):
            exif["focal_length"] = f"{fl:.0f} mm"

    title = tag_map.get("ImageDescription") or tag_map.get("XPTitle") or tag_map.get("Title")
    if isinstance(title, bytes):
        try:
            title = title.decode("utf-16").rstrip("\x00")
        except Exception:
            title = None
    if title:
        exif["title"] = str(title).strip()

    rating_tag = tag_map.get("Rating") or tag_map.get("RatingPercent")
    if rating_tag is not None:
        try:
            val = int(rating_tag[0] if isinstance(rating_tag, (list, tuple)) else rating_tag)
            if val > 5:                            # RatingPercent 0‑100 → 0‑5
                val = round(val / 20)
            exif["rating"] = val
        except Exception:
            pass

    return exif


# ── Variant generation ─────────────────────────────────────────────────────
TMP_ROOT       = Path(tempfile.gettempdir()) / "photo_variants"
VARIANT_DIRS   = {"thumbnail": TMP_ROOT / "thumb", "small": TMP_ROOT / "small"}
VARIANT_SIZES  = {"thumbnail": 400, "small": 1600}

def ensure_variant_file(base: Path, variant: str) -> Path:
    target_px = VARIANT_SIZES[variant]
    out_path  = VARIANT_DIRS[variant] / base.name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and out_path.stat().st_mtime >= base.stat().st_mtime:
        return out_path

    with Image.open(base) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((target_px, target_px), resample=Image.LANCZOS)
        save_kwargs: dict[str, Any] = {}
        if img.format == "JPEG":
            save_kwargs.update({"quality": 85, "optimize": True})
        img.save(out_path, **save_kwargs)
    return out_path


# ── Schemas ────────────────────────────────────────────────────────────────
class PhotoOut(BaseModel):
    id:            int
    name:          str
    original_url:  str
    small_url:     str | None = None
    thumbnail_url: str | None = None
    rating:        int | None = None
    title:         str | None = None
    camera:        str | None = None
    lens:          str | None = None
    iso:           int | None = None
    aperture:      str | None = None
    shutter_speed: str | None = None
    focal_length:  str | None = None
    created_at:    datetime

    class Config:
        orm_mode = True


# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(title="Photo API")

@app.get("/photos", response_model=list[PhotoOut])
def list_photos(db: Session = Depends(db_session)):
    return db.query(Photo).order_by(Photo.id.desc()).all()


@app.post("/photos", response_model=PhotoOut, status_code=201)
def upload_photo(
    file: UploadFile = File(...),
    rating: int | None = Form(None),
    title: str | None = Form(None),
    db: Session = Depends(db_session),
):
    # — Save upload to a temp file
    tmp_dir   = Path(tempfile.mkdtemp(prefix="photo_upload_"))
    original  = tmp_dir / file.filename
    with original.open("wb") as fh:
        for chunk in iter(lambda: file.file.read(8192), b""):
            fh.write(chunk)

    sha1  = file_sha1(original)
    size  = original.stat().st_size
    exif  = extract_exif(original)

    if rating is not None:
        exif["rating"] = rating
    if title is not None:
        exif["title"] = title

    # — Upload original + variants
    key_original  = f"full/{original.name}"
    url_original  = upload_file(original, key_original)

    urls: dict[str, str | None] = {"small": None, "thumbnail": None}
    for variant in VARIANT_DIRS:
        vfile = ensure_variant_file(original, variant)
        key   = f"{variant}/{vfile.name}"
        urls[variant] = upload_file(vfile, key)

    # — Persist DB row
    photo = Photo(
        name=original.name,
        sha1=sha1,
        size=size,
        original_url=url_original,
        small_url=urls["small"],
        thumbnail_url=urls["thumbnail"],
        created_at=datetime.utcnow(),
        **{k: exif.get(k) for k in ("rating","title","camera","lens","iso",
                                   "aperture","shutter_speed","focal_length")},
    )
    try:
        db.add(photo)
        db.flush()          # ← get auto‑ID
    except IntegrityError:
        raise HTTPException(status_code=409, detail="A photo with this name already exists")

    logger.info("Stored photo id=%s name=%s", photo.id, photo.name)
    return photo


@app.delete("/photos/{photo_id}", status_code=204,
            responses={404: {"description": "Not found"}})
def delete_photo(photo_id: int, db: Session = Depends(db_session)):
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # — Delete from S3
    delete_file(photo.original_url.split("/", 3)[-1])
    if photo.small_url:
        delete_file(photo.small_url.split("/", 3)[-1])
    if photo.thumbnail_url:
        delete_file(photo.thumbnail_url.split("/", 3)[-1])

    db.delete(photo)
    logger.info("Removed photo id=%s name=%s", photo.id, photo.name)
    return JSONResponse(status_code=204, content={})
