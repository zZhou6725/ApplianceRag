from urllib.parse import quote

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.db.session import get_db
from app.services.conversation_service import get_conversation
from app.services.export_service import conversation_to_markdown, conversation_to_pdf_bytes

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{conversation_id}/markdown")
def export_markdown(conversation_id: str, db: Session = Depends(get_db)):
    conv = get_conversation(db, conversation_id)
    content = conversation_to_markdown(conv)
    safe_name = quote(f"{conv.title}.md")
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}"},
    )


@router.get("/{conversation_id}/pdf")
def export_pdf(conversation_id: str, db: Session = Depends(get_db)):
    conv = get_conversation(db, conversation_id)
    pdf_bytes = conversation_to_pdf_bytes(conv)
    safe_name = quote(f"{conv.title}.pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}"},
    )