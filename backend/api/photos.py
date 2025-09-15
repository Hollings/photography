import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from deps import get_db
from models import Photo
from schemas import PhotoOut, PhotoUpdate
from utils.exif import extract_exif
from utils.hashing import file_sha1
from utils.image_variants import VariantBuilder
from utils.storage import S3Storage

router          = APIRouter()
variant_builder = VariantBuilder()
storage         = S3Storage()

@router.get("/photos", response_model=list[PhotoOut])
def list_photos(db: Session = Depends(get_db)):
    return (
        db.query(Photo)
          .order_by(Photo.sort_order.asc(), Photo.id.desc())
          .all()
    )

@router.post("/photos", response_model=PhotoOut, status_code=201)
def upload_photo(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    sort_order: int   = Form(0),
    db: Session       = Depends(get_db),
):
    tmp_dir  = Path(tempfile.mkdtemp(prefix="photo_upload_"))
    original = tmp_dir / file.filename
    with original.open("wb") as fh:
        for chunk in iter(lambda: file.file.read(8192), b""):
            fh.write(chunk)

    sha1  = file_sha1(original)
    size  = original.stat().st_size
    exif  = extract_exif(original)
    print("DEBUG EXIF:", exif)
    if title is not None:
        exif["title"] = title

    key_original = f"full/{original.name}"
    url_original = storage.upload_file(original, key_original)

    urls: Dict[str, Optional[str]] = {"thumbnail": None, "small": None, "medium": None}
    for variant in variant_builder.VARIANT_SPECS:
        vfile = variant_builder.ensure_variant(original, variant)
        key   = f"{variant}/{vfile.name}"
        urls[variant] = storage.upload_file(vfile, key)

    photo = Photo(
        name           = original.name,
        sha1           = sha1,
        size           = size,
        original_url   = url_original,
        medium_url     = urls["medium"],
        small_url      = urls["small"],
        thumbnail_url  = urls["thumbnail"],
        sort_order     = sort_order,
        created_at     = datetime.utcnow(),
        **{k: exif.get(k) for k in (
            "title", "camera", "lens", "iso",
            "aperture", "shutter_speed", "focal_length",
        )},
    )
    try:
        db.add(photo)
        db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="A photo with this name already exists")

    return photo

@router.patch("/photos/{photo_id}", response_model=PhotoOut)
def edit_photo(photo_id: int, payload: PhotoUpdate, db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    # Title update
    if payload.title is not None:
        photo.title = payload.title
    # Name (filename) update: rename S3 keys and update URLs
    if payload.name is not None:
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(status_code=422, detail="name cannot be empty")
        old_name = photo.name
        if new_name != old_name:
            # Preserve extension if caller omitted it
            if "." not in new_name and "." in old_name:
                ext = old_name.split(".")[-1]
                new_name = f"{new_name}.{ext}"

            # Prepare key remaps for each available variant
            def key_from_url(url: str) -> str:
                return url.split("/", 3)[-1]

            remaps: list[tuple[str, str, str]] = []  # (field, old_key, new_key)
            if photo.original_url:
                old_key = key_from_url(photo.original_url)
                prefix  = old_key.split("/", 1)[0]
                remaps.append(("original_url", old_key, f"{prefix}/{new_name}"))
            if photo.small_url:
                ok = key_from_url(photo.small_url)
                remaps.append(("small_url", ok, f"small/{new_name}"))
            if getattr(photo, "medium_url", None):
                ok = key_from_url(photo.medium_url)
                remaps.append(("medium_url", ok, f"medium/{new_name}"))
            if photo.thumbnail_url:
                ok = key_from_url(photo.thumbnail_url)
                remaps.append(("thumbnail_url", ok, f"thumbnail/{new_name}"))

            # Execute renames in S3
            for _, old_key, new_key in remaps:
                try:
                    storage.rename_file(old_key, new_key)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed renaming {old_key} -> {new_key}: {e}")

            # Update DB URLs
            for field, _, new_key in remaps:
                setattr(photo, field, storage.public_url(new_key))
            photo.name = new_name
    if payload.sort_order is not None:
        photo.sort_order = payload.sort_order
    db.add(photo)
    return photo

@router.delete("/photos/{photo_id}", status_code=204)
def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    storage.delete_file(photo.original_url.split("/", 3)[-1])
    if photo.small_url:
        storage.delete_file(photo.small_url.split("/", 3)[-1])
    if photo.thumbnail_url:
        storage.delete_file(photo.thumbnail_url.split("/", 3)[-1])

    db.delete(photo)
    return {}
