"""初始化数据库表结构。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import engine, Base
from app.models.db_models import ConversationRecord, MessageRecord  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成。")


if __name__ == "__main__":
    init_db()