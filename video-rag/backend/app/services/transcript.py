import asyncio
import json
import logging
import os
from html.parser import HTMLParser
from urllib.parse import quote_plus, urlparse, parse_qs

import httpx
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from app.services.metadata import compute_engagement_rate

logger = logging.getLogger(__name__)

# Export INSTAGRAM_COOKIES_FILE path in .env pointing to a Netscape-format cookies.txt.
# Export cookies from a logged-in browser session using the yt-dlp cookies guide.
INSTAGRAM_COOKIES_FILE = os.getenv("INSTAGRAM_COOKIES_FILE", "")


class _YouTubeMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_values: dict[str, list[str]] = {}
        self.json_ld_blobs: list[str] = []
        self._capture_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        tag = tag.lower()

        if tag == "meta":
            key = attr_map.get("property") or attr_map.get("name") or attr_map.get("itemprop")
            content = attr_map.get("content")
            if key and content:
                self.meta_values.setdefault(key.lower(), []).append(content.strip())
            return

        if tag == "link":
            key = attr_map.get("itemprop")
            href = attr_map.get("href")
            if key and href:
                self.meta_values.setdefault(key.lower(), []).append(href.strip())
            return

        if tag == "script" and (attr_map.get("type") or "").lower() == "application/ld+json":
            self._capture_json_ld = True
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_json_ld:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capture_json_ld:
            blob = "".join(self._json_ld_parts).strip()
            if blob:
                self.json_ld_blobs.append(blob)
            self._capture_json_ld = False
            self._json_ld_parts = []


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _collect_meta_values(parser: _YouTubeMetadataParser, *keys: str) -> str:
    for key in keys:
        values = parser.meta_values.get(key.lower()) or []
        for value in values:
            if value.strip():
                return value.strip()
    return ""


def _parse_json_ld_author_name(blob: str) -> str:
    try:
        data = json.loads(blob)
    except Exception:
        return ""

    candidates = data if isinstance(data, list) else [data]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        author = candidate.get("author")
        if isinstance(author, dict):
            name = author.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        publisher = candidate.get("publisher")
        if isinstance(publisher, dict):
            name = publisher.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return ""


def _parse_json_ld_thumbnail(blob: str) -> str:
    try:
        data = json.loads(blob)
    except Exception:
        return ""

    candidates = data if isinstance(data, list) else [data]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        thumbnail = candidate.get("thumbnailUrl") or candidate.get("image")
        if isinstance(thumbnail, str) and thumbnail.strip():
            return thumbnail.strip()
        if isinstance(thumbnail, list):
            for item in thumbnail:
                if isinstance(item, str) and item.strip():
                    return item.strip()
                if isinstance(item, dict):
                    url = item.get("url")
                    if isinstance(url, str) and url.strip():
                        return url.strip()
    return ""


def _fetch_http_text(url: str) -> str:
    timeout = httpx.Timeout(12.0, connect=5.0)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _fetch_youtube_oembed(url: str) -> dict:
    oembed_url = f"https://www.youtube.com/oembed?url={quote_plus(url)}&format=json"
    try:
        response = httpx.get(oembed_url, timeout=httpx.Timeout(10.0, connect=5.0))
        response.raise_for_status()
        payload = response.json()
        logger.info("YOUTUBE_METADATA_FALLBACK source=oembed url=%s", url)
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        logger.warning(
            "YOUTUBE_METADATA_FALLBACK source=oembed failed url=%s error=%s: %s",
            url,
            type(exc).__name__,
            exc,
        )
        return {}


def _fetch_youtube_watch_metadata(url: str) -> dict:
    try:
        html = _fetch_http_text(url)
    except Exception as exc:
        logger.warning(
            "YOUTUBE_METADATA_FALLBACK source=watch_page failed url=%s error=%s: %s",
            url,
            type(exc).__name__,
            exc,
        )
        return {}

    parser = _YouTubeMetadataParser()
    try:
        parser.feed(html)
    except Exception as exc:
        logger.warning(
            "YOUTUBE_METADATA_FALLBACK source=watch_page_parse failed url=%s error=%s: %s",
            url,
            type(exc).__name__,
            exc,
        )
        return {}

    json_ld_author = ""
    json_ld_thumbnail = ""
    for blob in parser.json_ld_blobs:
        if not json_ld_author:
            json_ld_author = _parse_json_ld_author_name(blob)
        if not json_ld_thumbnail:
            json_ld_thumbnail = _parse_json_ld_thumbnail(blob)

    return {
        "title": _first_non_empty(
            _collect_meta_values(parser, "og:title", "twitter:title"),
            _collect_meta_values(parser, "name"),
        ),
        "description": _first_non_empty(
            _collect_meta_values(parser, "og:description", "twitter:description"),
            _collect_meta_values(parser, "description"),
        ),
        "creator": _first_non_empty(
            _collect_meta_values(parser, "author", "channel_name", "channelname"),
            json_ld_author,
        ),
        "thumbnail": _first_non_empty(
            _collect_meta_values(parser, "og:image", "twitter:image"),
            json_ld_thumbnail,
        ),
    }


def _extract_thumbnail_urls(info: dict | None, video_id: str) -> tuple[str, list[str]]:
    if not info:
        logger.info("Thumbnail extracted for video %s: None", video_id)
        return "", []

    raw_thumbnail = info.get("thumbnail") or ""
    candidates: list[str] = []
    if raw_thumbnail:
        candidates.append(raw_thumbnail)

    thumbnails = info.get("thumbnails") or []
    for thumb in thumbnails:
        url = thumb.get("url") if isinstance(thumb, dict) else None
        if url:
            candidates.append(url)

    unique: list[str] = []
    seen: set[str] = set()
    for url in candidates:
        if url and url not in seen:
            seen.add(url)
            unique.append(url)

    primary = unique[0] if unique else ""
    alternates = unique[1:]

    logger.info("Thumbnail extracted for video %s: %s", video_id, raw_thumbnail or "None")
    if alternates:
        logger.info("Thumbnail alternates for video %s: %s", video_id, alternates)

    return primary, alternates


def _get_youtube_id(url: str) -> str | None:
    """
    Handles all YouTube URL formats:
    - youtube.com/watch?v=ID
    - youtu.be/ID
    - youtube.com/shorts/ID
    - youtube.com/embed/ID
    - m.youtube.com/watch?v=ID
    """
    parsed = urlparse(url)
    netloc = parsed.netloc.lower().replace("www.", "")

    if netloc == "youtu.be":
        vid = parsed.path.lstrip("/").split("?")[0]
        return vid or None

    if netloc in ("youtube.com", "m.youtube.com", "music.youtube.com"):
        # Standard: ?v=ID
        vid = parse_qs(parsed.query).get("v", [None])[0]
        if vid:
            return vid
        # Shorts and Embed: /shorts/ID or /embed/ID
        path_parts = [p for p in parsed.path.split("/") if p]
        for marker in ("shorts", "embed"):
            if marker in path_parts:
                idx = path_parts.index(marker)
                if idx + 1 < len(path_parts):
                    return path_parts[idx + 1]

    return None


def detect_platform(url: str) -> str:
    """Returns 'youtube', 'youtube_shorts', or 'instagram'."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower().replace("www.", "")

    if netloc in ("youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"):
        return "youtube_shorts" if "/shorts/" in parsed.path else "youtube"

    if netloc in ("instagram.com", "m.instagram.com"):
        return "instagram"

    return "unknown"


def _build_ydl_opts(platform: str) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "ignoreerrors": True,
    }
    if (
        platform == "instagram"
        and INSTAGRAM_COOKIES_FILE
        and os.path.exists(INSTAGRAM_COOKIES_FILE)
    ):
        opts["cookiefile"] = INSTAGRAM_COOKIES_FILE
        logger.info("Using Instagram cookies from %s", INSTAGRAM_COOKIES_FILE)
    return opts


def _safe_transcript(yt_id: str) -> str:
    try:
        segments = YouTubeTranscriptApi.get_transcript(yt_id)
        transcript = " ".join(s["text"] for s in segments)
        logger.info("YOUTUBE_TRANSCRIPT_SUCCESS yt_id=%s segments=%d", yt_id, len(segments))
        return transcript
    except Exception as e:
        logger.warning("YOUTUBE_TRANSCRIPT_FAILED yt_id=%s error=%s: %s", yt_id, type(e).__name__, e)
        return ""


def _safe_extract_info(url: str, platform: str) -> dict | None:
    try:
        with yt_dlp.YoutubeDL(_build_ydl_opts(platform)) as ydl:
            info = ydl.extract_info(url, download=False)
        if info is None:
            # ignoreerrors=True swallows the real error — log context to help diagnose
            if platform == "instagram":
                logger.warning(
                    "Instagram extraction returned None for %s. "
                    "This almost always means authentication is required. "
                    "Set INSTAGRAM_COOKIES_FILE in .env to fix this.",
                    url,
                )
            else:
                logger.warning("yt_dlp returned None for %s", url)
        return info
    except Exception as e:
        logger.warning(
            "yt_dlp extraction failed for %s: %s: %s", url, type(e).__name__, e
        )
        return None


def _default_data(url: str, video_id: str, platform: str) -> dict:
    """
    Returned when extraction fails. Ingestion continues with zero-value metadata
    rather than crashing the whole request.
    """
    return {
        "video_id": video_id,
        "url": url,
        "platform": platform,
        "transcript": "",
        "description": "",
        "title": "",
        "creator": "",
        "views": None,
        "likes": 0,
        "comments": 0,
        "follower_count": 0,
        "hashtags": [],
        "upload_date": "",
        "duration": 0,
        "thumbnail": "",
        "thumbnail_alternates": [],
        "engagement_rate": None,
    }


def extract_hashtags(text: str) -> list[str]:
    if not text:
        return []
    import re
    tags = re.findall(r"#(\w+)", text)
    return list(dict.fromkeys(tags))


def _fetch_youtube_sync(url: str, video_id: str) -> dict:
    platform = detect_platform(url)  # "youtube" or "youtube_shorts"
    yt_id = _get_youtube_id(url)
    transcript_text = _safe_transcript(yt_id) if yt_id else ""

    info = _safe_extract_info(url, platform)
    if info is None:
        oembed_data = _fetch_youtube_oembed(url)
        watch_data = _fetch_youtube_watch_metadata(url)
        data = _default_data(url, video_id, platform)
        data["transcript"] = transcript_text
        data["title"] = _first_non_empty(oembed_data.get("title"), watch_data.get("title"))
        data["creator"] = _first_non_empty(oembed_data.get("author_name"), watch_data.get("creator"))
        data["description"] = _first_non_empty(watch_data.get("description"))
        data["thumbnail"] = _first_non_empty(oembed_data.get("thumbnail_url"), watch_data.get("thumbnail"))
        data["thumbnail_alternates"] = [
            value
            for value in [oembed_data.get("thumbnail_url"), watch_data.get("thumbnail")]
            if isinstance(value, str) and value.strip() and value.strip() != data["thumbnail"]
        ]
        if data["description"]:
            data["hashtags"] = extract_hashtags(f"{data['title']} {data['description']}")

        logger.info(
            "YOUTUBE_METADATA_FALLBACK video_id=%s url=%s title=%s creator=%s thumbnail=%s",
            video_id,
            url,
            data["title"] or "",
            data["creator"] or "",
            data["thumbnail"] or "",
        )
        logger.info(
            "YOUTUBE_INGEST_COMPLETE video_id=%s url=%s metadata_source=fallback",
            video_id,
            url,
        )
        return data

    views = info.get("view_count") or 0
    likes = info.get("like_count") or 0
    comments = info.get("comment_count") or 0

    if views <= 0:
        views_val = None
        engagement_rate = None
    else:
        views_val = views
        engagement_rate = compute_engagement_rate(likes, comments, views)

    thumbnail, thumbnail_alternates = _extract_thumbnail_urls(info, video_id)

    logger.info(
        "YOUTUBE_METADATA_SUCCESS video_id=%s url=%s title=%s creator=%s thumbnail=%s",
        video_id,
        url,
        info.get("title") or "",
        info.get("uploader") or info.get("channel") or "",
        thumbnail or "",
    )
    logger.info(
        "YOUTUBE_INGEST_COMPLETE video_id=%s url=%s metadata_source=yt_dlp",
        video_id,
        url,
    )

    return {
        "video_id": video_id,
        "url": url,
        "platform": platform,
        "transcript": transcript_text,
        "description": info.get("description") or "",
        "title": info.get("title") or "",
        "creator": info.get("uploader") or "",
        "views": views_val,
        "likes": likes,
        "comments": comments,
        "follower_count": info.get("channel_follower_count") or 0,
        "hashtags": info.get("tags") or [],
        "upload_date": info.get("upload_date") or "",
        "duration": int(round(float(info.get("duration") or 0))),
        "thumbnail": thumbnail,
        "thumbnail_alternates": thumbnail_alternates,
        "engagement_rate": engagement_rate,
    }


def _fetch_instagram_sync(url: str, video_id: str) -> dict:
    platform = "instagram"
    info = _safe_extract_info(url, platform)

    if info is None:
        return _default_data(url, video_id, platform)

    views = info.get("view_count") or 0
    likes = info.get("like_count") or 0
    comments = info.get("comment_count") or 0

    # No caption track on Instagram — description is the best available text.
    transcript_text = info.get("description") or ""

    if views <= 0:
        views_val = None
        engagement_rate = None
    else:
        views_val = views
        engagement_rate = compute_engagement_rate(likes, comments, views)

    hashtags = info.get("tags") or []
    if not hashtags and transcript_text:
        hashtags = extract_hashtags(transcript_text)

    thumbnail, thumbnail_alternates = _extract_thumbnail_urls(info, video_id)

    return {
        "video_id": video_id,
        "url": url,
        "platform": platform,
        "transcript": transcript_text,
        "description": info.get("description") or "",
        "title": info.get("title") or "",
        "creator": info.get("uploader") or info.get("channel") or "",
        "views": views_val,
        "likes": likes,
        "comments": comments,
        "follower_count": info.get("channel_follower_count") or 0,
        "hashtags": hashtags,
        "upload_date": info.get("upload_date") or "",
        "duration": int(round(float(info.get("duration") or 0))),
        "thumbnail": thumbnail,
        "thumbnail_alternates": thumbnail_alternates,
        "engagement_rate": engagement_rate,
    }


async def fetch_video_data(url: str, video_id: str) -> dict:
    """
    Routes to YouTube or Instagram fetcher.
    _get_youtube_id() now handles Shorts — if it returns a value, it's YouTube.
    """
    loop = asyncio.get_event_loop()

    if _get_youtube_id(url) is not None:
        return await loop.run_in_executor(None, _fetch_youtube_sync, url, video_id)
    else:
        return await loop.run_in_executor(None, _fetch_instagram_sync, url, video_id)
