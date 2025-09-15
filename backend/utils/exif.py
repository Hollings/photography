from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import re

import exifread
from PIL import ExifTags, Image, ImageOps

# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
def _rational_to_float(value) -> Optional[float]:
    if isinstance(value, (tuple, list)) and len(value) == 2 and value[1]:
        return value[0] / value[1]
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _decode_if_bytes(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, bytes):
        for enc in ("utf-16le", "utf-8", "latin1"):
            try:
                return val.decode(enc).rstrip("\x00").strip()
            except Exception:  # pragma: no cover
                continue
        return None
    return str(val).strip()


def _first(tags: Dict[str, Any], *keys: str) -> Any:
    """Return the first present/truthy value among tag keys."""
    for k in keys:
        v = tags.get(k)
        if v:
            return v
    return None


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #
def extract_exif(path: Path) -> Dict[str, Any]:
    """
    Return a normalised subset of metadata:
      • camera  – camera model (maker stripped)
      • lens    – lens model
      • iso     – integer ISO
      • aperture – e.g. “f/2.8”
      • shutter_speed – e.g. “1/160 s”
      • focal_length  – e.g. “35 mm”
      • title   – XPTitle / Title / ImageDescription / XPSubject / Subject / Caption / Caption-Abstract
    """
    meta: Dict[str, Any] = {}

    # --------------------------------------------------------------------- #
    # pass 1 – exifread (handles JPEG/TIFF + most RAW, keeps Windows XP* )  #
    # --------------------------------------------------------------------- #
    try:
        with path.open("rb") as fh:
            tags = exifread.process_file(fh, details=False, stop_tag="UNDEF")  # fast
    except Exception:
        tags = {}

    if tags:
        # camera make/model ------------------------------------------------ #
        make  = _decode_if_bytes(tags.get("Image Make"))
        model = _decode_if_bytes(tags.get("Image Model"))
        if model:
            model_only = model
            if make and model_only.lower().startswith(make.lower()):
                model_only = model_only[len(make):].lstrip(" -_").strip()
            meta["camera"] = model_only

        # lens ------------------------------------------------------------- #
        lens = _decode_if_bytes(
            _first(tags,
                   "EXIF LensModel", "MakerNote LensModel", "Image LensModel")
        )
        if lens:
            meta["lens"] = lens

        # ISO -------------------------------------------------------------- #
        iso = tags.get("EXIF ISOSpeedRatings")
        if iso and iso.values:
            meta["iso"] = int(iso.values[0])

        # aperture --------------------------------------------------------- #
        fnum = tags.get("EXIF FNumber")
        if fnum:
            f = _rational_to_float(fnum.values[0])
            if f:
                meta["aperture"] = f"f/{f:.1f}"

        # shutter ---------------------------------------------------------- #
        shutter = tags.get("EXIF ExposureTime")
        if shutter:
            num = shutter.values[0]
            if isinstance(num, Fraction):
                meta["shutter_speed"] = f"{num.numerator}/{num.denominator} s"
            else:
                meta["shutter_speed"] = str(num)

        # focal length ----------------------------------------------------- #
        focal = tags.get("EXIF FocalLength")
        if focal:
            fl = _rational_to_float(focal.values[0])
            if fl:
                meta["focal_length"] = f"{fl:.0f} mm"

        # title / caption --------------------------------------------------- #
        title_tag = _first(
            tags,
            "Image XPTitle",
            "Image ImageDescription",
            "EXIF XPSubject",
            "Image XPSubject",
            "Image Subject",
            "Image Caption",
            "Image Caption-Abstract",
        )
        if title_tag:
            meta["title"] = _decode_if_bytes(title_tag.values if hasattr(title_tag, "values") else title_tag)

        # taken_at (DateTimeOriginal) -------------------------------------- #
        try:
            dt_tag = _first(tags, "EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime")
            if dt_tag:
                raw = dt_tag.values[0] if hasattr(dt_tag, "values") else dt_tag
                s = _decode_if_bytes(raw)
                if s and len(s) >= 19:  # format like 'YYYY:MM:DD HH:MM:SS'
                    s = s.replace("\x00", "").strip()
                    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                        try:
                            meta["taken_at"] = datetime.strptime(s, fmt)
                            break
                        except Exception:
                            continue
        except Exception:  # pragma: no cover
            pass

        # Do not return yet — we may still need to fill taken_at via
        # Pillow or XMP if EXIF DateTimeOriginal is missing.

    # --------------------------------------------------------------------- #
    # pass 2 – fallback to Pillow (JPEG/TIFF only)                           #
    # --------------------------------------------------------------------- #
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            raw = img._getexif() or {}
    except Exception:
        return meta

    tag_map = {ExifTags.TAGS.get(k, k): v for k, v in raw.items()}

    make  = _decode_if_bytes(tag_map.get("Make")) or ""
    model = _decode_if_bytes(tag_map.get("Model"))
    if model:
        camera_model = model
        if make and camera_model.lower().startswith(make.lower()):
            camera_model = camera_model[len(make):].lstrip(" -_").strip()
        meta["camera"] = camera_model

    if (lens := _decode_if_bytes(tag_map.get("LensModel"))):
        meta["lens"] = lens

    if (iso_val := tag_map.get("ISOSpeedRatings") or tag_map.get("PhotographicSensitivity")):
        iso = iso_val[0] if isinstance(iso_val, (list, tuple)) else iso_val
        if isinstance(iso, (int, float)):
            meta["iso"] = int(iso)

    if (fnum := tag_map.get("FNumber")) is not None:
        if (f := _rational_to_float(fnum)):
            meta["aperture"] = f"f/{f:.1f}"

    if (shutter := tag_map.get("ExposureTime")) is not None:
        if isinstance(shutter, (tuple, list)) and len(shutter) == 2 and shutter[1]:
            meta["shutter_speed"] = f"{shutter[0]}/{shutter[1]} s"
        else:
            meta["shutter_speed"] = str(shutter)

    if (focal := tag_map.get("FocalLength")) is not None:
        if (fl := _rational_to_float(focal)):
            meta["focal_length"] = f"{fl:.0f} mm"

    for field in (
        "XPTitle",
        "Title",
        "ImageDescription",
        "XPSubject",
        "Subject",
        "Caption",
        "Caption-Abstract",
    ):
        if (val := tag_map.get(field)):
            if (decoded := _decode_if_bytes(val)):
                meta["title"] = decoded
                break

    # taken_at -------------------------------------------------------------- #
    try:
        dt_raw = (
            tag_map.get("DateTimeOriginal")
            or tag_map.get("DateTime")
            or tag_map.get("DateTimeDigitized")
        )
        if dt_raw:
            s = _decode_if_bytes(dt_raw)
            if s and len(s) >= 19:
                s = s.replace("\x00", "").strip()
                for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        meta["taken_at"] = datetime.strptime(s, fmt)
                        break
                    except Exception:
                        continue
    except Exception:  # pragma: no cover
        pass

    # --------------------------------------------------------------------- #
    # pass 3 – minimal XMP sniff (LR may write XMP without EXIF)             #
    # --------------------------------------------------------------------- #
    if "taken_at" not in meta:
        try:
            # Read a larger chunk to find embedded XMP packet (some exports
            # place XMP later in the file). 8 MB is still fast and safe.
            with path.open("rb") as fh:
                blob = fh.read(8 * 1024 * 1024)
            try:
                text = blob.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
            if text:
                m = re.search(r'(?:xmp:CreateDate|photoshop:DateCreated)="([^"]+)"', text)
                if m:
                    s = m.group(1).strip()
                    # Normalise and parse ISO‑8601 (with timezone if present)
                    try:
                        dt = datetime.fromisoformat(s)
                        if dt.tzinfo is not None:
                            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                        meta["taken_at"] = dt
                    except Exception:
                        pass
        except Exception:  # pragma: no cover
            pass

    return meta
