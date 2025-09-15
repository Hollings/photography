from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PhotoOut(BaseModel):
    id:            int
    name:          str
    original_url:  str
    medium_url:    Optional[str] = None
    small_url:     Optional[str] = None
    thumbnail_url: Optional[str] = None
    sort_order:    int
    title:         Optional[str] = None
    camera:        Optional[str] = None
    lens:          Optional[str] = None
    iso:           Optional[int] = None
    aperture:      Optional[str] = None
    shutter_speed: Optional[str] = None
    focal_length:  Optional[str] = None
    # Prefer EXIF capture time when available
    taken_at:      Optional[datetime] = None
    created_at:    datetime
    # Feed/publication metadata
    posted_at:     Optional[datetime] = None
    post_title:    Optional[str] = None
    post_summary:  Optional[str] = None

    class Config:
        orm_mode = True


class PhotoUpdate(BaseModel):
    title:      Optional[str] = None
    name:       Optional[str] = None
    sort_order: Optional[int] = None


class PhotoPublish(BaseModel):
    post_title:   Optional[str] = None
    post_summary: Optional[str] = None
    posted_at:    Optional[datetime] = None  # if omitted, server uses now()
