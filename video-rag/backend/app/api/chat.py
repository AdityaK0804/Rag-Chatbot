import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.request import ChatRequest
from app.services.rag_chain import stream_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    logger.info(
        "Chat request | session=%s | question=%s",
        request.session_id,
        request.question[:60],
    )

    return StreamingResponse(
        stream_response(
            question=request.question,
            session_id=request.session_id,
            url_a=request.url_a,
            url_b=request.url_b,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Prevents Nginx from buffering the stream
        },
    )