from pydantic import BaseModel


class VideoMeta(BaseModel):
    video_id: str          # "A" or "B"
    url: str
    platform: str          # "youtube" or "instagram"
    title: str
    creator: str
    views: int | None = None
    likes: int
    comments: int
    follower_count: int
    hashtags: list[str]
    upload_date: str
    duration: int          # seconds
    thumbnail: str
    thumbnail_alternates: list[str] = []
    engagement_rate: float | None = None
    chunks_stored: int
    already_indexed: bool = False


class IngestResponse(BaseModel):
    status: str            # "ok"
    videos: dict[str, VideoMeta]   # {"A": VideoMeta, "B": VideoMeta}


class CitationSource(BaseModel):
    video_id: str          # "A" or "B"
    chunk_index: int
    preview: str           # first 120 chars of the chunk


class ChatResponse(BaseModel):
    # Only used for non-streaming fallback / testing.
    # The real chat endpoint streams SSE — this won't be the actual response type.
    answer: str
    sources: list[CitationSource]
    session_id: str
