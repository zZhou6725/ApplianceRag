"""Long-term conversation memory — stores summaries as vectors, supports semantic recall.

Creates a dedicated ChromaDB collection ("conversation_memory") separate from
the knowledge-base collection. Each memory entry stores a short LLM summary of
a conversation turn along with metadata (timestamp, topics).
"""

import json
import os
import time
from datetime import datetime

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from langchain_chroma import Chroma

from app.core.config import settings
from app.model.factory import chat_model, embed_model
from app.utils.logger_handler import logger
from app.utils.path_tools import get_abs_path

MEMORY_COLLECTION = "conversation_memory"
MEMORY_PERSIST_DIR = str(settings.chroma_dir) + "_memory"


class MemoryManager:
    """Manages long-term conversation memory via vector storage.

    Each turn (user query + assistant answer) is summarised by the LLM and
    stored as a vector. On subsequent turns, semantically similar past
    conversations are recalled and injected into the context.
    """

    def __init__(self):
        persist = MEMORY_PERSIST_DIR
        try:
            self._store = Chroma(
                collection_name=MEMORY_COLLECTION,
                embedding_function=embed_model,
                persist_directory=persist,
            )
        except Exception:
            logger.warning("[MemoryManager] ChromaDB 初始化失败，重建中...")
            if os.path.exists(persist):
                import shutil
                shutil.rmtree(persist)
            self._store = Chroma(
                collection_name=MEMORY_COLLECTION,
                embedding_function=embed_model,
                persist_directory=persist,
            )
        logger.info("[MemoryManager] 长期记忆模块初始化完成")

    def summarize(self, user_query: str, assistant_answer: str) -> str:
        """Generate a one-line summary of a conversation turn using the LLM."""
        prompt = (
            "用一句话（不超过 50 字）总结以下对话的核心内容，只输出这句话，不做任何解释。\n\n"
            f"用户: {user_query}\n"
            f"助手: {assistant_answer[:300]}\n"
        )
        try:
            result = chat_model.invoke(prompt)
            return result.content.strip()
        except Exception as e:
            logger.warning(f"[MemoryManager] 摘要生成失败: {e}")
            return user_query[:80]

    def store(self, user_query: str, assistant_answer: str, metadata: dict | None = None) -> str:
        """Summarise a turn and store it in the vector collection.

        Returns the memory ID.
        """
        summary = self.summarize(user_query, assistant_answer)
        meta = {
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query[:200],
            "summary": summary,
        }
        if metadata:
            meta.update(metadata)

        try:
            ids = self._store.add_texts(texts=[summary], metadatas=[meta])
            mem_id = ids[0] if ids else ""
            logger.info(f"[MemoryManager] 记忆已存储: {summary[:60]}")
            return mem_id
        except Exception as e:
            logger.error(f"[MemoryManager] 存储失败: {e}")
            return ""

    def recall(self, query: str, k: int = 3) -> list[dict]:
        """Retrieve semantically similar past conversations.

        Returns up to `k` memories, each as {summary, user_query, timestamp, score}.
        """
        try:
            docs = self._store.similarity_search_with_relevance_scores(query, k=k)
        except Exception as e:
            logger.warning(f"[MemoryManager] 检索失败: {e}")
            return []

        results = []
        for doc, score in docs:
            results.append({
                "summary": doc.metadata.get("summary", doc.page_content),
                "user_query": doc.metadata.get("user_query", ""),
                "timestamp": doc.metadata.get("timestamp", ""),
                "score": round(score, 4),
            })
        # Filter: keep results with relevance above threshold.
        # similarity_search_with_relevance_scores returns higher = more relevant.
        filtered = [r for r in results if r["score"] > 0.1]
        logger.info(f"[MemoryManager] 召回 {len(filtered)} 条相关记忆")
        return filtered[:k]

    def format_memories(self, memories: list[dict]) -> str:
        """Format recalled memories as a context string for the LLM."""
        if not memories:
            return ""
        lines = ["[历史对话记忆]"]
        for i, m in enumerate(memories, 1):
            ts = m["timestamp"][:10] if m["timestamp"] else "?"
            lines.append(f"{i}. ({ts}) {m['summary']}")
        return "\n".join(lines)

    def count(self) -> int:
        try:
            return self._store._collection.count()
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            all_ids = self._store.get()["ids"]
            if all_ids:
                self._store.delete(ids=all_ids)
            logger.info("[MemoryManager] 记忆已清空")
        except Exception as e:
            logger.error(f"[MemoryManager] 清空失败: {e}")


# Global singleton
memory_manager = MemoryManager()
