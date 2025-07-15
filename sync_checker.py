#!/usr/bin/env python3
"""
Continuously watch `./photos` and keep an S3 bucket, `photos.json`,
and a GitHub Pages site in sync.

Required environment variables (see .env):
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, S3_BUCKET
  GITHUB_TOKEN, GH_REPO (e.g. "username/repo"), GH_BRANCH (e.g. "gh-pages")
  POLL_SECONDS  – integer polling interval; defaults to 10 s
"""

import os
import json
import time
import mimetypes
import hashlib
import subprocess
from pathlib import Path
from dotenv import load_dotenv

import boto3

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
PHOTOS_DIR   = Path("./photos").resolve()
META_FILE    = Path("site/photos.json")
INDEX_FILE   = Path("site/index.html")

AWS_REGION   = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
S3_BUCKET    = os.getenv("S3_BUCKET")

GH_TOKEN     = os.getenv("GITHUB_TOKEN")
GH_REPO      = os.getenv("GH_REPO")          # "owner/repo"
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


# ── Helpers ────────────────────────────────────────────────────────────────────
def file_sha1(path: Path) -> str:
    """Return SHA‑1 hex digest of a file (streamed)."""
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def public_url(key: str) -> str:
    # If the bucket is public, the standard virtual‑hosted–style URL works:
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


def load_metadata() -> dict:
    """
    Always return a dict keyed by photo filename, even if the existing JSON
    file is an empty list (`[]`) or an old list‑style structure.
    """
    if META_FILE.exists() and META_FILE.stat().st_size:
        with META_FILE.open() as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            # Previous versions may have stored a list;
            # convert it safely to the new dict layout.
            return {entry["name"]: entry for entry in data if "name" in entry}
    return {}


def save_metadata(meta: dict) -> None:
    META_FILE.write_text(json.dumps(meta, indent=2, sort_keys=True))


def generate_index(meta: dict) -> None:
    """Regenerate a very small static index.html from metadata."""
    lines = [
        "<!doctype html><html><head>",
        "<meta charset='utf-8'><title>Photo Gallery</title>",
        "<style>body{font-family:sans-serif} img{max-width:250px;margin:4px}</style>",
        "</head><body><h1>Photo Gallery</h1>",
    ]
    for entry in meta.values():
        lines.append(f"<div><img src='{entry['url']}' alt='{entry['name']}'></div>")
    lines.append("</body></html>")
    INDEX_FILE.write_text("\n".join(lines))


def git_cmd(*args: str) -> None:
    subprocess.run(["git", *args], check=True)


def commit_and_push(msg: str) -> None:
    git_cmd("add", str(META_FILE), str(INDEX_FILE))
    git_cmd("-c", "user.email=actions@localhost", "-c", "user.name=photo-sync-bot",
            "commit", "-m", msg)
    remote_url = f"https://{GH_TOKEN}@github.com/{GH_REPO}.git"
    # Ensure the correct remote is present
    try:
        git_cmd("remote", "set-url", "origin", remote_url)
    except subprocess.CalledProcessError:
        git_cmd("remote", "add", "origin", remote_url)
    git_cmd("push", "origin", f"HEAD:{GH_BRANCH}")


def upload_file(path: Path, key: str) -> None:
    mimetype, _ = mimetypes.guess_type(path.name)
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
    s3.delete_object(Bucket=S3_BUCKET, Key=key)


# ── Main loop ──────────────────────────────────────────────────────────────────
def scan_local_photos() -> dict[str, dict]:
    """
    Return mapping:
      {<filename>: {"name": <filename>, "path": Path, "sha1": <sha1>}}
    Only image files (basic extensions).
    """
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
    result = {}
    for p in PHOTOS_DIR.glob("*"):
        if p.suffix.lower() in exts and p.is_file():
            result[p.name] = {"name": p.name, "path": p, "sha1": file_sha1(p)}
    return result


def sync_once() -> bool:
    """Run one sync cycle. Return True if any change occurred."""
    local = scan_local_photos()
    meta  = load_metadata()

    # Determine changes
    local_names  = set(local)
    remote_names = set(meta)

    added   = local_names - remote_names
    removed = remote_names - local_names
    maybe_modified = local_names & remote_names

    changed = False

    # Upload new files
    for name in added:
        entry = local[name]
        upload_file(entry["path"], name)
        meta[name] = {
            "name": name,
            "url": public_url(name),
            "sha1": entry["sha1"],
            "size": entry["path"].stat().st_size,
        }
        changed = True

    # Detect modifications (hash change)
    for name in maybe_modified:
        entry = local[name]
        if entry["sha1"] != meta[name].get("sha1"):
            upload_file(entry["path"], name)
            meta[name]["sha1"] = entry["sha1"]
            meta[name]["size"] = entry["path"].stat().st_size
            changed = True

    # Remove deleted files
    for name in removed:
        delete_file(name)
        del meta[name]
        changed = True

    if changed:
        save_metadata(meta)
        generate_index(meta)

    return changed


def main() -> None:
    PHOTOS_DIR.mkdir(exist_ok=True)
    while True:
        if sync_once():
            print("Change detected – committing and pushing...")
            try:
                commit_and_push("Sync photos")
            except subprocess.CalledProcessError as e:
                print("Git push failed:", e)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
