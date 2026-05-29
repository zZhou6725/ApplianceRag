"""将知识库文档加载到 ChromaDB 向量数据库。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.vector_store import VectorStoreService


def ingest() -> None:
    store = VectorStoreService()
    store.load_document()
    print("知识库加载完成。")


if __name__ == "__main__":
    ingest()
