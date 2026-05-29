import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.db_models import ConversationRecord, MessageRecord
from app.models.schemas import (
    ConversationListItem,
    ConversationListResponse,
    ConversationResponse,
    MessageData,
)


def create_conversation(db: Session, title: str = "新对话") -> str:
    conv_id = uuid.uuid4().hex[:12]
    record = ConversationRecord(conversation_id=conv_id, title=title)
    db.add(record)
    db.commit()
    return conv_id


def add_message(db: Session, conversation_id: str, role: str, content: str) -> MessageData:
    msg_id = uuid.uuid4().hex[:12]
    record = MessageRecord(
        message_id=msg_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    db.add(record)

    conv = (
        db.query(ConversationRecord)
        .filter(ConversationRecord.conversation_id == conversation_id)
        .first()
    )
    if conv:
        conv.updated_at = datetime.now(timezone.utc)
        if conv.title == "新对话" and role == "user":
            conv.title = content[:50]

    db.commit()
    return MessageData(
        message_id=msg_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=record.created_at,
    )


def get_conversation(db: Session, conversation_id: str) -> ConversationResponse:
    conv = (
        db.query(ConversationRecord)
        .filter(ConversationRecord.conversation_id == conversation_id)
        .first()
    )
    if conv is None:
        raise NotFoundError(message="对话不存在")

    messages = (
        db.query(MessageRecord)
        .filter(MessageRecord.conversation_id == conversation_id)
        .order_by(MessageRecord.created_at.asc())
        .all()
    )
    return ConversationResponse(
        conversation_id=conv.conversation_id,
        title=conv.title,
        messages=[
            MessageData(
                message_id=m.message_id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def list_conversations(db: Session) -> ConversationListResponse:
    records = (
        db.query(ConversationRecord)
        .order_by(ConversationRecord.updated_at.desc())
        .all()
    )
    items = []
    for record in records:
        count = (
            db.query(func.count(MessageRecord.id))
            .filter(MessageRecord.conversation_id == record.conversation_id)
            .scalar()
        )
        items.append(
            ConversationListItem(
                conversation_id=record.conversation_id,
                title=record.title,
                message_count=count or 0,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )
    return ConversationListResponse(total=len(items), items=items)


def delete_conversation(db: Session, conversation_id: str) -> bool:
    db.query(MessageRecord).filter(
        MessageRecord.conversation_id == conversation_id
    ).delete()

    conv = (
        db.query(ConversationRecord)
        .filter(ConversationRecord.conversation_id == conversation_id)
        .first()
    )
    if conv is None:
        raise NotFoundError(message="对话不存在")

    db.delete(conv)
    db.commit()
    return True