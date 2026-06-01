import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.models.request import IngestRequest
from app.models.response import IngestResponse, VideoMeta
from app.services.gemini_errors import get_gemini_user_message
from app.services.transcript import fetch_video_data
from app.services.vector_store import store_chunks, get_chunk_count, delete_video_chunks
from app.utils.cache import is_cached, mark_cached, clear_cache
from app.services.rag_chain import clear_session_state
from app.utils.chunker import get_chunks, get_metadata_fallback_chunk

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

    # Clear previous state and database entries for A and B
    clear_session_state()
    clear_cache()
    delete_video_chunks("A")
    delete_video_chunks("B")

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
            transcript = data.get("transcript") or ""
            description = data.get("description") or ""
            hashtags = data.get("hashtags") or []
            
            logger.info("DEBUG: Video %s - transcript length: %d, description length: %d, hashtags: %d",
                        vid, len(transcript), len(description), len(hashtags))
            
            chunks = []
            
            # 1. Transcript chunks
            if transcript.strip():
                t_chunks = get_chunks(transcript)
                chunks.extend({"text": chunk, "source_type": "transcript"} for chunk in t_chunks)
                logger.info("DEBUG: Video %s - created %d transcript chunks", vid, len(t_chunks))
                
                # 2. Description chunks (if not duplicate of transcript)
                transcript_clean = " ".join(transcript.strip().split())
                description_clean = " ".join(description.strip().split())
                if description_clean and description_clean != transcript_clean:
                    d_chunks = get_chunks(description)
                    for dc in d_chunks:
                        chunks.append({"text": f"Description: {dc}", "source_type": "description"})
                    logger.info("DEBUG: Video %s - created %d description chunks", vid, len(d_chunks))
                
                # 3. Hashtags chunk
                if hashtags:
                    chunks.append({"text": "Hashtags: " + ", ".join(hashtags), "source_type": "hashtags"})
                    logger.info("DEBUG: Video %s - added hashtags chunk", vid)
            else:
                chunks.append({
                    "text": get_metadata_fallback_chunk(data),
                    "source_type": "metadata_fallback",
                })
                logger.info("DEBUG: Video %s - created metadata fallback chunk", vid)
                
            logger.info("DEBUG: Video %s - total chunks compiled: %d", vid, len(chunks))

            try:
                chunks_stored = await store_chunks(data, chunks)
            except Exception as exc:
                user_message = get_gemini_user_message(exc)
                if user_message:
                    logger.warning("Gemini embedding failed during ingestion: %s", user_message)
                    raise HTTPException(status_code=503, detail=user_message) from exc
                raise
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
            thumbnail_alternates=data.get("thumbnail_alternates") or [],
            engagement_rate=data["engagement_rate"],
            chunks_stored=chunks_stored,
            already_indexed=already_indexed,
        )
        logger.info(
            "Thumbnail sent to frontend for video %s: %s (alternates=%d)",
            vid,
            data.get("thumbnail") or "None",
            len(data.get("thumbnail_alternates") or []),
        )

    # Log/print the active video titles
    title_a = videos["A"].title if "A" in videos else "None"
    title_b = videos["B"].title if "B" in videos else "None"
    logger.info("ACTIVE VIDEO A:\n%s", title_a)
    logger.info("ACTIVE VIDEO B:\n%s", title_b)
    print(f"ACTIVE VIDEO A:\n{title_a}")
    print(f"ACTIVE VIDEO B:\n{title_b}")

    return IngestResponse(status="ok", videos=videos)
