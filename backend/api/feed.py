from datetime import datetime, timezone
from typing import List, Tuple

from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.orm import Session
import mimetypes
from urllib.parse import urlparse

from deps import get_db
from models import Photo
from config import s3_client, S3_BUCKET

router = APIRouter()


def _rfc2822(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


def _to_cee_image(url: str) -> str:
    # Map S3 URLs to cee.photography/images/<key> for nicer feed URLs
    try:
        from urllib.parse import urlparse
        u = urlparse(url)
        if "amazonaws.com" in (u.hostname or ""):
            return f"https://cee.photography/images{u.path}"
    except Exception:
        pass
    return url


def _s3_bucket_and_key_from_url(url: str) -> Tuple[str, str]:
    # Parse S3 URL of form https://<bucket>.s3.<region>.amazonaws.com/<key>
    try:
        u = urlparse(url)
        host = u.hostname or ""
        key = u.path.lstrip("/")
        if ".s3." in host and host.endswith("amazonaws.com"):
            bucket = host.split(".s3.", 1)[0]
            return bucket, key
    except Exception:
        pass
    # Fallback to configured bucket and derived key (might be wrong if non-S3 URL)
    return S3_BUCKET, url.split("/", 3)[-1]


def _mime_for_key(key: str) -> str:
    mt, _ = mimetypes.guess_type(key)
    return mt or "application/octet-stream"


@router.get("/feed.xml")
def feed(request: Request, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    # Determine scheme/host from proxy headers or request URL
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "https"
    host  = request.headers.get("host") or request.url.netloc or "cee.photography"
    base  = f"{proto}://{host}"
    q = (
        db.query(Photo)
          .filter(Photo.posted_at.isnot(None))
          .filter(Photo.posted_at <= now)
          .order_by(Photo.posted_at.desc(), Photo.id.desc())
          .limit(50)
          .all()
    )

    items: List[str] = []
    last_build = None
    for p in q:
        if not p.posted_at:
            continue
        if last_build is None or p.posted_at > last_build:
            last_build = p.posted_at
        link = f"{base}/p/{p.id}"
        title = p.post_title or p.title or p.name
        desc = p.post_summary or ""
        guid = link  # per-host GUID using permalink
        pub  = _rfc2822(p.posted_at)
        # Prefer medium image; fall back to original
        chosen_url = p.medium_url or p.original_url
        # Map to current host for nicer URLs
        try:
            u = urlparse(chosen_url)
            if "amazonaws.com" in (u.hostname or ""):
                enclosure_url = f"{base}/images{u.path}"
            else:
                enclosure_url = chosen_url
        except Exception:
            enclosure_url = chosen_url
        # Determine length and content-type via S3 HEAD (best-effort)
        length = 0
        ctype  = _mime_for_key(urlparse(chosen_url).path)
        try:
            bucket, key = _s3_bucket_and_key_from_url(chosen_url)
            head = s3_client.head_object(Bucket=bucket, Key=key)
            length = int(head.get("ContentLength", 0))
            ctype  = head.get("ContentType", ctype) or ctype
        except Exception:
            pass

        items.append(
            "".join([
                "<item>",
                f"<title>{_xml_escape(title)}</title>",
                f"<link>{_xml_escape(link)}</link>",
                f"<guid isPermaLink=\"true\">{_xml_escape(guid)}</guid>",
                f"<pubDate>{pub}</pubDate>",
                f"<description>{_xml_escape(desc)}</description>",
                f"<enclosure url=\"{_xml_escape(enclosure_url)}\" length=\"{length}\" type=\"{_xml_escape(ctype)}\" />",
                "</item>",
            ])
        )

    last_build = last_build or now
    rss = "".join([
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<rss version=\"2.0\" xmlns:atom=\"http://www.w3.org/2005/Atom\">",
        "<channel>",
        "<title>CEE Photography</title>",
        f"<link>{_xml_escape(base)}/</link>",
        "<description>Curated photos by CEE</description>",
        f"<atom:link href=\"{_xml_escape(base)}/feed.xml\" rel=\"self\" type=\"application/rss+xml\" />",
        f"<lastBuildDate>{_rfc2822(last_build)}</lastBuildDate>",
        *items,
        "</channel>",
        "</rss>",
    ])

    return Response(content=rss, media_type="application/rss+xml; charset=utf-8")
