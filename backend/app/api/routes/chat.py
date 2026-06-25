from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.schemas import ChatRequest
from app.services.chat_service import stream_chat
from app.utils.logger_handler import logger

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream", summary="流式聊天 (SSE)", description="发送用户消息并返回 SSE 流式响应，每个 token 作为事件推送，结束时发送 done 事件附带 conversation_id")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    logger.info("[API] 收到消息: conv=%s msg=%.100s file=%s",
                request.conversation_id or "(新)",
                request.message,
                request.file_name or "(无)")
    return StreamingResponse(
        stream_chat(
            db,
            request.conversation_id,
            request.message,
            file_context=request.file_context,
            file_name=request.file_name,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )