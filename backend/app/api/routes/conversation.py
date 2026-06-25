from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.response import success
from app.services.conversation_service import (
    delete_conversation,
    get_conversation,
    list_conversations,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", summary="对话列表", description="获取当前用户的所有对话，按更新时间倒序排列")
def list_all(db: Session = Depends(get_db)):
    result = list_conversations(db)
    return success(data=result.model_dump())


@router.get("/{conversation_id}", summary="对话详情", description="获取指定对话的完整内容，包含所有消息历史")
def get_detail(conversation_id: str, db: Session = Depends(get_db)):
    result = get_conversation(db, conversation_id)
    return success(data=result.model_dump())


@router.delete("/{conversation_id}", summary="删除对话", description="删除指定对话及其所有消息")
def delete_one(conversation_id: str, db: Session = Depends(get_db)):
    delete_conversation(db, conversation_id)
    return success(message="已删除")