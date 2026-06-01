import asyncio
import logging
import os
from urllib.parse import urlparse, parse_qs

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

from app.services.metadata import compute_engagement_rate

logger = logging.getLogger(__name__)

# Export INSTAGRAM_COOKIES_FILE path in .env pointing to a Netscape-format cookies.txt.
# Export cookies from a logged-in browser session using the yt-dlp cookies guide.
INSTAGRAM_COOKIES_FILE = os.getenv("INSTAGRAM_COOKIES_FILE", "")


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
        return " ".join(s["text"] for s in segments)
    except Exception as e:
        logger.warning(
            "Transcript unavailable for %s: %s: %s", yt_id, type(e).__name__, e
        )
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
        data = _default_data(url, video_id, platform)
        data["transcript"] = transcript_text
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
        "thumbnail": info.get("thumbnail") or "",
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
        "thumbnail": info.get("thumbnail") or "",
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