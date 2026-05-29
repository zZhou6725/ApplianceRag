"""向后兼容模块 —— 推荐直接使用 app.core.config 和 app.db.session。"""
from app.core.config import settings, get_settings
from app.db.session import Base, engine, SessionLocal, init_db, get_db

BACKEND_DIR = settings.__class__.BACKEND_DIR if hasattr(settings.__class__, "BACKEND_DIR") else None

__all__ = [
    "settings",
    "get_settings",
    "Base",
    "engine",
    "SessionLocal",
    "init_db",
    "get_db",
]