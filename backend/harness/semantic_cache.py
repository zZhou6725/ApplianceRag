"""语义缓存层：用 embedding 相似度匹配替代精确哈希匹配。

两层缓存：
1. 答案缓存 — 相似度 > 0.95 直接复用 LLM 回答（跳过 LLM 调用）
2. 文档缓存 — 相似度 > 0.90 复用检索文档（跳过向量检索，仍需 LLM 总结）

降级路径：语义缓存 miss → 精确哈希缓存 → 完整 RAG 流程
"""
import math
import os
import time

from app.utils.logger_handler import logger


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """纯 Python 余弦相似度，避免依赖 numpy。"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticCache:
    """基于 embedding 相似度的双层语义缓存。"""

    def __init__(
        self,
        answer_threshold: float = 0.95,
        doc_threshold: float = 0.90,
        max_entries: int = 500,
    ):
        self._answer_threshold = answer_threshold
        self._doc_threshold = doc_threshold
        self._max_entries = max_entries

        # 答案缓存: [{query, embedding, answer, ts}]
        self._answers: list[dict] = []
        # 文档缓存: [{query, embedding, docs, ts}]
        self._docs: list[dict] = []

        # 统计
        self._semantic_hits = 0
        self._doc_hits = 0
        self._semantic_misses = 0
        self._lazy_embed_model = None

    @property
    def _embed_model(self):
        """延迟加载 embedding 模型，避免启动时阻塞。"""
        if self._lazy_embed_model is None:
            from app.model.factory import embed_model
            self._lazy_embed_model = embed_model
        return self._lazy_embed_model

    def _find_similar(self, query_emb: list[float], store: list[dict], threshold: float) -> dict | None:
        """在 store 中查找最相似的条目，超过阈值则返回。"""
        best = None
        best_sim = 0.0
        for entry in store:
            sim = _cosine_sim(query_emb, entry["embedding"])
            if sim > best_sim:
                best_sim = sim
                best = entry
        if best and best_sim >= threshold:
            logger.info("[SemanticCache] 语义命中 sim=%.4f query=%.50s", best_sim, best["query"])
            return best
        return None

    def _add_to_store(self, store: list[dict], entry: dict):
        store.append(entry)
        if len(store) > self._max_entries:
            store.pop(0)

    # ── 答案缓存 ────────────────────────────────────────────────

    def get_answer(self, query: str) -> str | None:
        """语义相似度查找缓存的 LLM 回答。"""
        try:
            emb = self._embed_model.embed_query(query)
        except Exception:
            self._semantic_misses += 1
            return None

        match = self._find_similar(emb, self._answers, self._answer_threshold)
        if match:
            self._semantic_hits += 1
            return match["answer"]

        self._semantic_misses += 1
        return None

    def set_answer(self, query: str, answer: str):
        try:
            emb = self._embed_model.embed_query(query)
            self._add_to_store(self._answers, {
                "query": query,
                "embedding": emb,
                "answer": answer,
                "ts": time.time(),
            })
        except Exception as e:
            logger.warning("[SemanticCache] 缓存答案失败: %s", e)

    # ── 文档缓存 ────────────────────────────────────────────────

    def get_docs(self, query: str) -> list | None:
        """语义相似度查找缓存的检索文档。返回文档列表或 None。"""
        try:
            emb = self._embed_model.embed_query(query)
        except Exception:
            return None

        match = self._find_similar(emb, self._docs, self._doc_threshold)
        if match:
            self._doc_hits += 1
            return match["docs"]
        return None

    def set_docs(self, query: str, docs: list):
        try:
            emb = self._embed_model.embed_query(query)
            self._add_to_store(self._docs, {
                "query": query,
                "embedding": emb,
                "docs": docs,
                "ts": time.time(),
            })
        except Exception as e:
            logger.warning("[SemanticCache] 缓存文档失败: %s", e)

    # ── 统计 ────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        total_answer = self._semantic_hits + self._semantic_misses
        return {
            "semantic_answer_hits": self._semantic_hits,
            "semantic_answer_misses": self._semantic_misses,
            "semantic_answer_rate": round(self._semantic_hits / total_answer, 4) if total_answer else 0.0,
            "doc_cache_hits": self._doc_hits,
            "answer_cache_size": len(self._answers),
            "doc_cache_size": len(self._docs),
        }

    def clear(self):
        self._answers.clear()
        self._docs.clear()
        self._semantic_hits = 0
        self._doc_hits = 0
        self._semantic_misses = 0


# 全局单例 — 阈值可通过环境变量微调
_answer_thr = float(os.getenv("SEMANTIC_ANSWER_THRESHOLD", "0.90"))
_doc_thr = float(os.getenv("SEMANTIC_DOC_THRESHOLD", "0.85"))
semantic_cache = SemanticCache(answer_threshold=_answer_thr, doc_threshold=_doc_thr)