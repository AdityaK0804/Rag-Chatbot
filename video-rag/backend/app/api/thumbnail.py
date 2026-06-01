import logging
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid thumbnail URL.")
    return url


async def _fetch_thumbnail_status(url: str) -> dict:
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.head(url)
            if resp.status_code == 405:
                resp = await client.get(url)
        except httpx.TimeoutException:
            logger.warning("Thumbnail failed: Timeout url=%s", url)
            raise HTTPException(status_code=504, detail="Thumbnail request timed out.")
        except httpx.RequestError as exc:
            logger.warning("Thumbnail failed: RequestError %s url=%s", exc, url)
            raise HTTPException(status_code=502, detail="Thumbnail request failed.")

    status = resp.status_code
    content_type = resp.headers.get("content-type") or ""
    final_url = str(resp.url)

    if status >= 400:
        logger.warning("Thumbnail failed: status=%s url=%s", status, url)
    else:
        logger.info("Thumbnail status: %s url=%s", status, url)

    return {
        "status": status,
        "ok": resp.is_success,
        "content_type": content_type,
        "final_url": final_url,
    }


@router.get("/thumbnail")
async def proxy_thumbnail(
    url: str = Query(..., description="Original thumbnail URL"),
    mode: str | None = Query(default=None, description="Use 'status' for diagnostics"),
):
    target_url = _validate_url(url)

    if mode == "status":
        return await _fetch_thumbnail_status(target_url)

    timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(target_url)
        except httpx.TimeoutException:
            logger.warning("Thumbnail failed: Timeout url=%s", target_url)
            raise HTTPException(status_code=504, detail="Thumbnail request timed out.")
        except httpx.RequestError as exc:
            logger.warning("Thumbnail failed: RequestError %s url=%s", exc, target_url)
            raise HTTPException(status_code=502, detail="Thumbnail request failed.")

    status = resp.status_code
    if status >= 400:
        logger.warning("Thumbnail failed: status=%s url=%s", status, target_url)
        raise HTTPException(status_code=502, detail=f"Thumbnail fetch failed ({status}).")

    content_type = resp.headers.get("content-type") or "image/jpeg"
    logger.info("Thumbnail rendered via proxy: status=%s url=%s", status, target_url)
    return StreamingResponse(
        iter([resp.content]),
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
