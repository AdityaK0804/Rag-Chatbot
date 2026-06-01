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
                "hashtags": meta.get("hashtags", "").split(",") if meta.get("hashtags") else [],
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

def get_all_chunks_for_video_id(video_id: str) -> list[dict]:
    """
    Directly pull all transcript/content chunks for a given video ID from ChromaDB,
    ordered by chunk_index.
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = client.get_collection(COLLECTION_NAME)
        res = collection.get(where={"video_id": video_id}, include=["metadatas", "documents"])
        
        chunks = []
        for doc_id, meta, doc in zip(res.get("ids", []), res.get("metadatas", []), res.get("documents", [])):
            # Skip empty or default placeholder chunks
            if doc.startswith("[No transcript available"):
                continue
            chunks.append({
                "text": doc,
                "metadata": meta,
                "score": 1.0,
                "source": f"Video {meta.get('video_id')} — chunk {meta.get('chunk_index')}",
            })
        
        chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
        return chunks
    except Exception as e:
        logger.warning("Failed to get all chunks for video_id %s: %s", video_id, e)
        return []


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
        video_id_filter = "A"
    elif video_filter == "B":
        video_id_filter = "B"
    else:
        video_id_filter = ["A", "B"]

    # 1. Get semantically relevant chunks from similarity search
    similarity_chunks = query_chunks(question, video_id_filter=video_id_filter, n_results=n_results)

    # 2. Get direct chunks for the active URLs to ensure content is always present
    direct_chunks = []
    if video_filter == "A" or video_filter is None:
        direct_chunks.extend(get_all_chunks_for_video_id("A"))
    if video_filter == "B" or video_filter is None:
        direct_chunks.extend(get_all_chunks_for_video_id("B"))

    # 3. Merge and deduplicate chunks by their text content
    seen_texts = set()
    merged_chunks = []
    
    for c in similarity_chunks:
        text_sig = c["text"].strip()
        if text_sig not in seen_texts:
            seen_texts.add(text_sig)
            merged_chunks.append(c)
            
    for c in direct_chunks:
        text_sig = c["text"].strip()
        if text_sig not in seen_texts:
            seen_texts.add(text_sig)
            merged_chunks.append(c)

    # Sort merged chunks: Video A chunks first (ordered by chunk_index), then Video B chunks (ordered by chunk_index)
    def sort_key(chunk):
        video_id = chunk["metadata"].get("video_id", "A")
        chunk_idx = chunk["metadata"].get("chunk_index", 0)
        return (video_id, chunk_idx)

    merged_chunks.sort(key=sort_key)

    logger.info(
        "Retrieved %d total chunks (similarity=%d, direct=%d) | filter=%s | question=%s",
        len(merged_chunks), len(similarity_chunks), len(direct_chunks), video_filter, question[:60],
    )
    return merged_chunks