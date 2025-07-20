from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import ExifTags, Image, ImageOps


def _rational_to_float(value) -> Optional[float]:
    if isinstance(value, (tuple, list)) and len(value) == 2 and value[1]:
        return value[0] / value[1]
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def extract_exif(path: Path) -> Dict[str, Any]:
    exif: Dict[str, Any] = {}
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            raw  = img._getexif() or {}
    except Exception:
        return exif

    tag_map = {ExifTags.TAGS.get(k, k): v for k, v in raw.items()}

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
                title = title.decode("utf‑16").rstrip("\x00")
            except Exception:
                title = None
    if title:
        exif["title"] = str(title).strip()

    return exif
