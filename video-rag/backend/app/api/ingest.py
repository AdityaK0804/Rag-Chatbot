import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.models.request import IngestRequest
from app.models.response import IngestResponse, VideoMeta
from app.services.transcript import fetch_video_data
from app.services.vector_store import store_chunks, get_chunk_count
from app.utils.cache import is_cached, mark_cached
from app.utils.chunker import get_chunks

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_videos(request: IngestRequest):
    logger.info("Ingestion started: %s | %s", request.url_a, request.url_b)

    results = await asyncio.gather(
        fetch_video_data(request.url_a, "A"),
        fetch_video_data(request.url_b, "B"),
        return_exceptions=True,
    )

    videos = {}

    for data in results:
        if isinstance(data, Exception):
            logger.error("fetch_video_data failed: %s", data)
            raise HTTPException(status_code=422, detail=str(data))

        vid = data["video_id"]
       

        if is_cached(data["url"]):
            logger.info("Video %s already in ChromaDB, skipping embed", vid)
            chunks_stored = get_chunk_count(data["url"])
            already_indexed = True
        else:
            already_indexed = False
            # Temporary debug logging
            transcript = data.get("transcript") or ""
            logger.info("DEBUG: Video %s - transcript length: %d", vid, len(transcript))
            logger.info("DEBUG: Video %s - transcript preview (first 300 chars): %s", vid, transcript[:300])
            
            chunks = get_chunks(transcript)
            logger.info("DEBUG: Video %s - number of chunks created: %d", vid, len(chunks))
            if chunks:
                logger.info("DEBUG: Video %s - first chunk preview: %s", vid, chunks[0][:300])
            else:
                logger.info("DEBUG: Video %s - no chunks created", vid)
                
            logger.info("DEBUG: Video %s - number of chunks sent to vector store: %d", vid, len(chunks))
            
            # Ensure at least one placeholder chunk is stored so metadata is cached in ChromaDB
            if not chunks:
                logger.info("DEBUG: Video %s - storing placeholder chunk for metadata caching", vid)
                chunks = [f"[No transcript available for Video {vid}]"]

            chunks_stored = await store_chunks(data, chunks)
            logger.info("DEBUG: Video %s - number of chunks actually stored: %d", vid, chunks_stored)
            mark_cached(data["url"])

        logger.info("Video %s — engagement: %s%%", vid, data["engagement_rate"])
        videos[vid] = VideoMeta(
            video_id=data["video_id"],
            url=data["url"],
            platform=data["platform"],
            title=data["title"],
            creator=data["creator"],
            views=data["views"],
            likes=data["likes"],
            comments=data["comments"],
            follower_count=data["follower_count"],
            hashtags=data["hashtags"],
            upload_date=data["upload_date"],
            duration=data["duration"],
            thumbnail=data["thumbnail"],
            engagement_rate=data["engagement_rate"],
            chunks_stored=chunks_stored,
            already_indexed=already_indexed,
        )

    return IngestResponse(status="ok", videos=videos)