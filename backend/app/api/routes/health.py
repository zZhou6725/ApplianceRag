from fastapi import APIRouter

from app.core.response import success

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return success(message="ok")