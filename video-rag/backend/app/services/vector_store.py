import hashlib
import logging
import os

import chromadb
from langchain_chroma import Chroma

from app.services.embedder import get_embedder

logger = logging.getLogger(__name__)

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
COLLECTION_NAME = "video_chunks"


def _get_raw_collection() -> chromadb.Collection:
    """
    Raw ChromaDB client for writes.
    We use upsert() here — LangChain's add_texts() calls add() which
    errors on duplicate IDs. Upsert is idempotent: re-ingesting the
    same video overwrites rather than duplicates.
    """
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def get_langchain_store() -> Chroma:
    """LangChain Chroma wrapper used for retrieval and as_retriever()."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embedder(),
        persist_directory=CHROMA_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )


def get_chunk_count(url: str) -> int:
    """
    Query the raw collection to get the count of chunks currently stored for a given URL.
    Returns 0 if the query fails or if no chunks exist.
    """
    try:
        collection = _get_raw_collection()
        results = collection.get(where={"url": url})
        return len(results.get("ids", []))
    except Exception as e:
        logger.warning("Failed to get chunk count for url %s: %s", url, e)
        return 0


async def store_chunks(data: dict, chunks: list[str]) -> int:
    """
    Embed chunks and upsert into ChromaDB.
    Returns number of chunks stored.
    """
    if not chunks:
        logger.warning("No chunks to store for video %s", data.get("video_id"))
        return 0

    embedder = get_embedder()

    # aembed_documents batches all chunks into a single OpenAI API call.
    vectors = await embedder.aembed_documents(chunks)

    ids = [
        hashlib.md5(f"{data['url']}:chunk:{i}".encode()).hexdigest()
        for i in range(len(chunks))
    ]

    metadatas = [
        {
            "video_id": data["video_id"],
            "url": data["url"],
            "platform": data["platform"],
            "creator": data["creator"],
            "chunk_index": i,
            # ChromaDB metadata values must be str/int/float/bool.
            "engagement_rate": str(data["engagement_rate"]) if data.get("engagement_rate") is not None else "None",
            "views": str(data["views"]) if data.get("views") is not None else "None",
            "likes": str(data["likes"]) if data.get("likes") is not None else "0",
            "title": data.get("title") or "",
            "comments": str(data.get("comments") or 0),
            "duration": str(data.get("duration") or 0),
            "hashtags": ",".join(data.get("hashtags") or []),
        }
        for i in range(len(chunks))
    ]

    collection = _get_raw_collection()
    collection.upsert(
        ids=ids,
        embeddings=vectors,
        documents=chunks,
        metadatas=metadatas,
    )

    logger.info("Stored %d chunks for video %s", len(chunks), data["video_id"])
    return len(chunks)


def query_chunks(
    question: str,
    video_id_filter: str | list[str] | None = None,
    n_results: int = 5,
) -> list[dict]:
    """
    Retrieve top-n chunks relevant to the question.
    video_id_filter: a single video ID ("A" or "B") or list of video IDs to filter by.
    """
    store = get_langchain_store()

    search_kwargs: dict = {"k": n_results}
    if video_id_filter:
        if isinstance(video_id_filter, list):
            search_kwargs["filter"] = {"video_id": {"$in": video_id_filter}}
        else:
            search_kwargs["filter"] = {"video_id": video_id_filter}

    results = store.similarity_search_with_relevance_scores(
        question, **search_kwargs
    )

    filtered_results = []
    for doc, score in results:
        # Ignore placeholder chunks from LLM context and citations
        if doc.page_content.startswith("[No transcript available"):
            continue
        filtered_results.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": round(score, 4),
            "source": f"Video {doc.metadata.get('video_id')} — chunk {doc.metadata.get('chunk_index')}",
        })

    return filtered_results


def get_retriever(video_filter: str | None = None):
    """LangChain-compatible retriever for use inside the RAG chain."""
    store = get_langchain_store()
    search_kwargs: dict = {"k": 5}
    if video_filter:
        search_kwargs["filter"] = {"video_id": video_filter}
    return store.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs,
    )


def delete_video_chunks(video_id: str):
    """
    Delete all chunks matching the given video_id ('A' or 'B') from ChromaDB.
    """
    try:
        collection = _get_raw_collection()
        collection.delete(where={"video_id": video_id})
        logger.info("Deleted all existing chunks for video %s from ChromaDB", video_id)
    except Exception as e:
        logger.warning("Failed to delete chunks for video %s: %s", video_id, e)