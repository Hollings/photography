from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from deps import get_db
from models import Photo

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


@router.get("/feed.xml")
def feed(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    q = (
        db.query(Photo)
          .filter(Photo.posted_at.isnot(None))
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
        link = f"https://cee.photography/p/{p.id}"
        title = p.post_title or p.title or p.name
        desc = p.post_summary or ""
        guid = f"cee.photography:photo:{p.id}"
        pub  = _rfc2822(p.posted_at)
        # Prefer medium image; fall back to original
        enclosure_url = p.medium_url or p.original_url

        items.append(
            "".join([
                "<item>",
                f"<title>{_xml_escape(title)}</title>",
                f"<link>{_xml_escape(link)}</link>",
                f"<guid isPermaLink=\"false\">{_xml_escape(guid)}</guid>",
                f"<pubDate>{pub}</pubDate>",
                f"<description>{_xml_escape(desc)}</description>",
                f"<enclosure url=\"{_xml_escape(enclosure_url)}\" type=\"image/jpeg\" />",
                "</item>",
            ])
        )

    last_build = last_build or now
    rss = "".join([
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<rss version=\"2.0\">",
        "<channel>",
        "<title>CEE Photography</title>",
        "<link>https://cee.photography/</link>",
        "<description>Curated photos by CEE</description>",
        f"<lastBuildDate>{_rfc2822(last_build)}</lastBuildDate>",
        *items,
        "</channel>",
        "</rss>",
    ])

    return Response(content=rss, media_type="application/rss+xml; charset=utf-8")

