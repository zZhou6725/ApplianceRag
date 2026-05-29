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


@router.get("")
def list_all(db: Session = Depends(get_db)):
    result = list_conversations(db)
    return success(data=result.model_dump())


@router.get("/{conversation_id}")
def get_detail(conversation_id: str, db: Session = Depends(get_db)):
    result = get_conversation(db, conversation_id)
    return success(data=result.model_dump())


@router.delete("/{conversation_id}")
def delete_one(conversation_id: str, db: Session = Depends(get_db)):
    delete_conversation(db, conversation_id)
    return success(message="已删除")