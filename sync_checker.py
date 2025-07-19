#!/usr/bin/env python3
"""
Continuously watch `./photos` and keep an S3 bucket, `photos.json`,
and a GitHub Pages docs site in sync.

• On every run, *always* refresh selected EXIF metadata (camera model,
  lens model, ISO, aperture, shutter speed, focal length, **rating**, title).

• Automatically creates mid‑sized (“small”, max 1600 px) and thumbnail
  (“thumbnail”, max 400 px) copies of every image, uploads them to S3,
  and records their URLs in `photos.json`.

Structured logging is provided; the log level is controlled with the
`LOG_LEVEL` environment variable (defaults to `INFO`).
"""

import os
import json
import time
import mimetypes
import hashlib
import subprocess
import logging
from fractions import Fraction
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import boto3
from PIL import Image, ImageOps, ExifTags          # Pillow ≥ 10 required
from xml.etree import ElementTree as ET

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
PHOTOS_DIR   = Path("./photos").resolve()
META_FILE    = Path("docs/photos.json")
INDEX_FILE   = Path("docs/index.html")

# Derivative image directories (relative to ``PHOTOS_DIR``)
VARIANT_DIRS = {
    "thumbnail": PHOTOS_DIR / "thumb",
    "small":     PHOTOS_DIR / "small",
    "full":      PHOTOS_DIR / "full",
}

# Target longest‑edge pixel sizes for automatically‑generated variants
VARIANT_SIZES = {
    "thumbnail": 400,     # ≤ 400 px
    "small":     1600,    # ≤ 1600 px  (a good mid‑size for retina displays)
    # “full” is *not* down‑sized – original file is used
}

AWS_REGION   = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
S3_BUCKET    = os.getenv("S3_BUCKET")

GH_TOKEN     = os.getenv("GITHUB_TOKEN")
GH_REPO      = os.getenv("GH_REPO")          # “owner/repo”
GH_BRANCH    = os.getenv("GH_BRANCH", "gh-pages")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "10"))

if not all([S3_BUCKET, GH_TOKEN, GH_REPO]):
    raise RuntimeError("Missing one or more required environment variables.")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# ── Helpers ────────────────────────────────────────────────────────────────
def file_sha1(path: Path) -> str:
    """Return SHA‑1 hex digest of *path* (streamed)."""
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def public_url(key: str) -> str:
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


def key_from_url(url: str) -> str:
    """Extract the S3 key from a URL produced by :func:`public_url`."""
    prefix = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/"
    return url[len(prefix):] if url.startswith(prefix) else url


def find_variant_file(base: Path, variant: str) -> Path | None:
    """Return the *first* variant file that already exists on disk."""
    candidates = [
        VARIANT_DIRS[variant] / base.name,
        base.with_name(f"{base.stem}-{variant}{base.suffix}"),
        base.with_name(f"{base.stem}_{variant}{base.suffix}"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


# ── Variant generation ─────────────────────────────────────────────────────
def ensure_variant_file(base: Path, variant: str) -> Path | None:
    """
    Return a path to an existing or newly‑created variant image.

    For “thumbnail” and “small”, an up‑to‑date resized copy is produced
    whenever it is missing *or* older than the source file.
    For “full”, no resizing is done and :func:`find_variant_file` is used.
    """
    if variant == "full":
        return find_variant_file(base, variant)

    target_px = VARIANT_SIZES[variant]
    out_path  = VARIANT_DIRS[variant] / base.name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Up‑to‑date file already exists
    if out_path.exists() and out_path.stat().st_mtime >= base.stat().st_mtime:
        return out_path

    try:
        with Image.open(base) as img:
            img = ImageOps.exif_transpose(img)  # auto‑orient
            img.thumbnail((target_px, target_px), resample=Image.LANCZOS)
            save_kwargs: dict[str, Any] = {}
            if img.format == "JPEG":
                save_kwargs.update({"quality": 85, "optimize": True})
            img.save(out_path, **save_kwargs)
        logger.info("Generated %s variant for %s", variant, base.name)
        return out_path
    except Exception as exc:                      # noqa: BLE001
        logger.error("Variant generation failed for %s (%s): %s", base, variant, exc)
        return None


def sync_variants(base: Path, name: str, meta_entry: dict, *, force: bool = False) -> None:
    """Create / upload thumbnail & small variants and update metadata."""
    for variant in VARIANT_DIRS:
        path  = ensure_variant_file(base, variant)
        field = f"{variant}_url"
        if path:
            key = path.relative_to(PHOTOS_DIR).as_posix()
            url = public_url(key)
            if force or meta_entry.get(field) != url:
                upload_file(path, key)
                meta_entry[field] = url
        else:
            if field in meta_entry:
                delete_file(key_from_url(meta_entry[field]))
                del meta_entry[field]

# ── Metadata helpers ───────────────────────────────────────────────────────
def load_metadata() -> dict:
    if META_FILE.exists() and META_FILE.stat().st_size:
        with META_FILE.open() as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):               # legacy list format
            logger.debug("Converting legacy list metadata format to dict")
            return {e["name"]: e for e in data if "name" in e}
    return {}


def save_metadata(meta: dict) -> None:
    META_FILE.write_text(json.dumps(meta, indent=2, sort_keys=True))
    logger.info("Metadata saved to %s", META_FILE)


# ── Git helpers ────────────────────────────────────────────────────────────
def git_cmd(*args: str) -> None:
    logger.debug("git %s", " ".join(args))
    subprocess.run(["git", *args], check=True)


def commit_and_push(msg: str) -> None:
    logger.info("Committing and pushing changes: %s", msg)
    git_cmd("add", str(META_FILE), str(INDEX_FILE))
    git_cmd("-c", "user.email=actions@localhost", "-c", "user.name=photo-sync-bot",
            "commit", "-m", msg)
    remote_url = f"https://{GH_TOKEN}@github.com/{GH_REPO}.git"
    try:
        git_cmd("remote", "set-url", "origin", remote_url)
    except subprocess.CalledProcessError:
        git_cmd("remote", "add", "origin", remote_url)
    git_cmd("push", "origin", f"HEAD:{GH_BRANCH}")

# ── S3 helpers ─────────────────────────────────────────────────────────────
def upload_file(path: Path, key: str) -> None:
    mimetype, _ = mimetypes.guess_type(path.name)
    logger.info("Uploading %s to S3 (key=%s)…", path.name, key)
    s3.upload_file(
        str(path),
        S3_BUCKET,
        key,
        ExtraArgs={
            "ContentType": mimetype or "application/octet-stream",
            "ACL": "public-read",
        },
    )


def delete_file(key: str) -> None:
    logger.info("Deleting %s from S3", key)
    s3.delete_object(Bucket=S3_BUCKET, Key=key)

# ── EXIF parsing helpers ───────────────────────────────────────────────────
def _rational_to_float(value) -> float | None:
    """Convert an EXIF rational (tuple or Fraction) to float safely."""
    if isinstance(value, (tuple, list)) and len(value) == 2 and value[1]:
        return value[0] / value[1]
    if isinstance(value, Fraction):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None
# ── EXIF parsing helpers ───────────────────────────────────────────────────
def _walk_xmp_dict(node: Any, exif: dict) -> None:
    """
    Recursively traverse an XMP dict (as returned by Pillow ≥ 10) and
    pull out a **rating** (integer 0‑5) and **title** (string).

    The structure can be deeply nested, e.g.:

        {'xmpmeta': {'RDF': {'Description': {'Rating': '5',
                                             'dc:title': {'Alt': {'li': 'My Title'}}}}}}

    The traversal stops as soon as both fields have been found.
    """
    if not isinstance(node, (dict, list)):
        return

    if isinstance(node, dict):
        for key, value in node.items():
            k = key.lower()

            # --- Rating (0‑5) ------------------------------------------------
            if k.endswith("rating") and "rating" not in exif:
                try:
                    exif["rating"] = int(value)
                except (TypeError, ValueError):
                    pass

            # --- Title ------------------------------------------------------
            if k.endswith("title") and "title" not in exif:
                # Various Lightroom / XMP flavours:
                #  • {'title': 'My Title'}
                #  • {'dc:title': {'Alt': {'li': 'My Title'}}}
                #  • {'description': {'Alt': {'li': {...}}}}
                if isinstance(value, str):
                    exif["title"] = value.strip()
                elif isinstance(value, dict):
                    alt = value.get("Alt") or value.get("alt")
                    if isinstance(alt, dict):
                        li = alt.get("li") or alt.get("LI")
                        if isinstance(li, str):
                            exif["title"] = li.strip()
                # Fall‑through for other nested cases

            # Recurse until both fields found
            if "rating" in exif and "title" in exif:
                return
            _walk_xmp_dict(value, exif)

    elif isinstance(node, list):
        for item in node:
            if "rating" in exif and "title" in exif:
                return
            _walk_xmp_dict(item, exif)


def _parse_xmp_xml(xml_bytes: bytes | str, exif: dict) -> None:
    """Parse raw XMP XML (string or bytes) for rating & title."""
    try:
        root = ET.fromstring(xml_bytes)
        ns = {
            "dc":  "http://purl.org/dc/elements/1.1/",
            "xmp": "http://ns.adobe.com/xap/1.0/",
        }
        rating_el = root.find(".//xmp:Rating", ns)
        title_el  = root.find(".//dc:title/*", ns)

        if rating_el is not None and rating_el.text and "rating" not in exif:
            exif["rating"] = int(rating_el.text.strip())

        if title_el is not None and title_el.text and "title" not in exif:
            exif["title"] = title_el.text.strip()
    except Exception:          # noqa: BLE001
        pass  # Ignore any XMP parse errors


def extract_exif(path: Path) -> dict:
    """
    Return a dict with selected EXIF & XMP fields
    (camera, lens, ISO, aperture, shutter_speed, focal_length, title, rating).
    Works whether Pillow returns XMP as a dict (≥ 10) or raw XML/bytes.
    """
    exif: dict[str, str | int | float] = {}

    try:
        with Image.open(path) as img:
            raw_exif = img._getexif() or {}
            xmp_obj  = img.getxmp() or {}            # may be dict / str / bytes / {}
            xmp_raw  = img.info.get("XML:com.adobe.xmp")  # fallback → bytes or None
    except Exception as exc:                         # noqa: BLE001
        logger.debug("EXIF extraction failed opening %s: %s", path, exc)
        return exif

    # ── XMP (dict form) ────────────────────────────────────────────────────
    if isinstance(xmp_obj, dict) and xmp_obj:
        _walk_xmp_dict(xmp_obj, exif)

    # ── XMP (raw XML) ──────────────────────────────────────────────────────
    if ("rating" not in exif or "title" not in exif):
        if isinstance(xmp_obj, (bytes, str)) and xmp_obj:
            _parse_xmp_xml(xmp_obj, exif)
        elif xmp_raw:
            _parse_xmp_xml(xmp_raw, exif)

    # ── Standard EXIF tags (unchanged from previous version) ───────────────
    tag_map = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}

    model = tag_map.get("Model")
    if model:
        exif["camera"] = str(model).strip()

    lens_model = tag_map.get("LensModel")
    if lens_model:
        exif["lens"] = str(lens_model).strip()

    iso_val = tag_map.get("ISOSpeedRatings") or tag_map.get("PhotographicSensitivity")
    if iso_val:
        iso = iso_val[0] if isinstance(iso_val, (list, tuple)) else iso_val
        exif["iso"] = int(iso)

    fnum = tag_map.get("FNumber")
    if fnum is not None:
        f = _rational_to_float(fnum)
        if f:
            exif["aperture"] = f"f/{f:.1f}"

    shutter = tag_map.get("ExposureTime")
    if shutter is not None:
        if isinstance(shutter, (tuple, list)) and len(shutter) == 2 and shutter[1]:
            exif["shutter_speed"] = f"{shutter[0]}/{shutter[1]} s"
        else:
            exif["shutter_speed"] = str(shutter)

    focal = tag_map.get("FocalLength")
    if focal is not None:
        fl = _rational_to_float(focal)
        if fl:
            exif["focal_length"] = f"{fl:.0f} mm"

    title = (
        tag_map.get("ImageDescription")
        or tag_map.get("XPTitle")
        or tag_map.get("Title")
    )
    if isinstance(title, bytes):
        try:
            title = title.decode("utf-16").rstrip("\x00")
        except Exception:                           # noqa: BLE001
            title = None
    if title and "title" not in exif:
        exif["title"] = str(title).strip()

    # ── Windows/Microsoft rating tags ──────────────────────────────────────
    rating_tag = tag_map.get("Rating") or tag_map.get("RatingPercent")
    if rating_tag is not None and "rating" not in exif:
        try:
            rating_val = int(
                rating_tag[0] if isinstance(rating_tag, (list, tuple)) else rating_tag
            )
            # RatingPercent is 0‑100 → convert to 0‑5 scale
            if rating_val > 5:
                rating_val = round(rating_val / 20)
            exif["rating"] = rating_val
        except Exception:                           # noqa: BLE001
            pass

    return exif


# ── Main loop helpers ──────────────────────────────────────────────────────
def scan_local_photos() -> dict[str, dict]:
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
    result = {}
    for p in PHOTOS_DIR.glob("*"):
        if p.suffix.lower() in exts and p.is_file():
            result[p.name] = {
                "name": p.name,
                "path": p,
                "sha1": file_sha1(p),
                "exif": extract_exif(p),
            }
    logger.debug("Scanned %d local photo(s)", len(result))
    return result


def sync_once() -> bool:
    """Synchronise local folder, S3 bucket & metadata. Returns True if changed."""
    logger.info("Starting sync cycle")
    local = scan_local_photos()
    meta  = load_metadata()

    local_names   = set(local)
    remote_names  = set(meta)

    added          = local_names - remote_names
    removed        = remote_names - local_names
    maybe_modified = local_names & remote_names

    changed = False

    # — Upload new files
    for name in added:
        entry = local[name]
        upload_file(entry["path"], name)
        meta[name] = {
            "name":  name,
            "url":   public_url(name),
            "sha1":  entry["sha1"],
            "size":  entry["path"].stat().st_size,
            **entry["exif"],            # includes `rating`
        }
        # Ensure `rating` is always present (None when absent) so that the
        # photos.json schema is stable and predictable.
        meta[name].setdefault("rating", None)
        sync_variants(entry["path"], name, meta[name], force=True)
        logger.info("Added %s", name)
        changed = True

    # — Detect content and/or metadata changes
    for name in maybe_modified:
        entry      = local[name]
        meta_entry = meta[name]

        sha_changed  = entry["sha1"] != meta_entry.get("sha1")
        exif_changed = False

        # keep a copy so we can check removals later
        original_keys = set(meta_entry)

        for k, v in entry["exif"].items():
            if meta_entry.get(k) != v:
                meta_entry[k] = v
                exif_changed = True

        # Remove obsolete keys (including rating if it disappeared)
        obsolete_keys = {
            "camera", "lens", "iso", "aperture",
            "shutter_speed", "focal_length", "title", "rating",
        } - entry["exif"].keys()
        for k in obsolete_keys:
            if k in meta_entry:
                del meta_entry[k]
                exif_changed = True

        # Guarantee that the JSON record contains a `rating` field even
        # when no rating exists in the file.
        if "rating" not in meta_entry:
            meta_entry["rating"] = None
            if "rating" not in original_keys:
                exif_changed = True

        if sha_changed:
            upload_file(entry["path"], name)
            meta_entry["sha1"] = entry["sha1"]
            meta_entry["size"] = entry["path"].stat().st_size
            sync_variants(entry["path"], name, meta_entry, force=True)
            logger.info("Updated content of %s", name)
        else:
            sync_variants(entry["path"], name, meta_entry)

        if exif_changed and not sha_changed:
            logger.info("Updated EXIF metadata for %s", name)

        if sha_changed or exif_changed:
            changed = True

    # — Remove deleted files
    for name in removed:
        meta_entry = meta[name]
        delete_file(name)
        for variant in VARIANT_DIRS:
            url_field = f"{variant}_url"
            if url_field in meta_entry:
                delete_file(key_from_url(meta_entry[url_field]))
        del meta[name]
        logger.info("Removed %s", name)
        changed = True

    if changed:
        save_metadata(meta)
    else:
        logger.info("No changes detected")

    return changed

# ── Entrypoint ─────────────────────────────────────────────────────────────
def main() -> None:
    PHOTOS_DIR.mkdir(exist_ok=True)
    logger.info("Photo sync service started ‒ polling every %d s", POLL_SECONDS)
    while True:
        try:
            if sync_once():
                try:
                    commit_and_push("Sync photos (content / metadata / variants)")
                except subprocess.CalledProcessError as exc:   # noqa: BLE001
                    logger.error("Git push failed: %s", exc)
        except Exception as exc:                               # noqa: BLE001
            logger.exception("Unexpected error during sync: %s", exc)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
