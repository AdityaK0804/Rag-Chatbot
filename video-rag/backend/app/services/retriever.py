import logging
import os

import chromadb

from app.services.vector_store import query_chunks

logger = logging.getLogger(__name__)

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
COLLECTION_NAME = "video_chunks"

def get_video_metadata(url_or_id: str) -> dict:
    """
    Pull stored metadata from the first chunk belonging to this video URL or video ID ("A" or "B").
    Avoids needing a separate metadata store — the data is already in ChromaDB.
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = client.get_collection(COLLECTION_NAME)
        
        # Support searching by either url or video_id
        if url_or_id in ("A", "B"):
            where_clause = {"video_id": url_or_id}
        else:
            where_clause = {"url": url_or_id}

        results = collection.get(
            where=where_clause,
            limit=1,
            include=["metadatas"],
        )
        if results["metadatas"]:
            meta = results["metadatas"][0]
            
            def to_int(val):
                if val is None or val == "None" or val == "":
                    return None
                try:
                    return int(float(val))
                except ValueError:
                    return None
            
            def to_float(val):
                if val is None or val == "None" or val == "":
                    return None
                try:
                    return float(val)
                except ValueError:
                    return None

            return {
                "video_id": meta.get("video_id"),
                "url": meta.get("url"),
                "platform": meta.get("platform"),
                "creator": meta.get("creator") or "",
                "title": meta.get("title") or "",
                "views": to_int(meta.get("views")),
                "likes": to_int(meta.get("likes")) or 0,
                "comments": to_int(meta.get("comments")) or 0,
                "duration": to_int(meta.get("duration")) or 0,
                "engagement_rate": to_float(meta.get("engagement_rate")),
            }
    except Exception as e:
        logger.warning("Could not fetch metadata for video %s: %s", url_or_id, e)
    return {}

def detect_video_filter(question: str) -> str | None:
    """
    Returns "A", "B", or None.
    None means the question is comparative — retrieve from both videos.
    """
    q = question.lower()
    has_a = "video a" in q
    has_b = "video b" in q

    if has_a and not has_b:
        return "A"
    if has_b and not has_a:
        return "B"
    return None

def retrieve(
    question: str,
    url_a: str,
    url_b: str,
    n_results: int = 5,
) -> list[dict]:
    """
    Retrieve relevant chunks. Applies video filter for single-video questions,
    searches both for comparative ones, limited to the specific URLs.
    """
    video_filter = detect_video_filter(question)
    
    if video_filter == "A":
        url_filter = url_a
    elif video_filter == "B":
        url_filter = url_b
    else:
        url_filter = [url_a, url_b]

    chunks = query_chunks(question, url_filter=url_filter, n_results=n_results)

    logger.info(
        "Retrieved %d chunks | filter=%s | question=%s",
        len(chunks), video_filter, question[:60],
    )
    return chunks