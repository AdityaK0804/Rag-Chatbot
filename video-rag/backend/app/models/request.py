from pydantic import BaseModel, HttpUrl, field_validator


class IngestRequest(BaseModel):
    url_a: str
    url_b: str

    @field_validator("url_a", "url_b")
    @classmethod
    def must_be_youtube_or_instagram(cls, v: str) -> str:
        v = v.strip()
        allowed = ("youtube.com", "youtu.be", "instagram.com")
        if not any(domain in v for domain in allowed):
            raise ValueError("URL must be a YouTube or Instagram link.")
        return v


class ChatRequest(BaseModel):
    question: str
    session_id: str
    # Passed from frontend after ingestion so the chain knows
    # which videos are loaded in the current session.
    url_a: str
    url_b: str

    @field_validator("question")
    @classmethod
    def question_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty.")
        return v