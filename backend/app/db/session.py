"""数据库引擎与会话管理 —— 统一入口，通过 FastAPI 依赖注入使用。"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

_database_url = settings.DATABASE_URL or f"sqlite:///{settings.db_path.as_posix()}"

engine = create_engine(
    _database_url,
    connect_args={"check_same_thread": False} if "sqlite" in _database_url else {},
    pool_size=5,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入获取数据库会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建所有表（于应用启动时调用）。"""
    Base.metadata.create_all(bind=engine)