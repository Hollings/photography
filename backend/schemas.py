from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PhotoOut(BaseModel):
    id:            int
    name:          str
    original_url:  str
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
    created_at:    datetime

    class Config:
        orm_mode = True


class PhotoUpdate(BaseModel):
    title:      Optional[str] = None
    sort_order: Optional[int] = None
