"""RAG 评测模块 —— chunk 级 Precision/MRR、文档级 Recall/Hit、LLM 缓存。"""
import hashlib
import json
import os
import time
from functools import lru_cache

from app.core.config import settings
from app.model.factory import embed_model
from app.rag.vector_store import VectorStoreService
from app.utils.logger_handler import logger


def _source_key(doc) -> str:
    """取 metadata.source 的文件名部分。"""
    source = doc.metadata.get("source", "")
    return os.path.basename(source)


def _chunk_matches(doc, keywords: list[str]) -> bool:
    """检查 chunk 内容是否包含任一关键词。"""
    if not keywords:
        return False
    content = doc.page_content
    return any(kw in content for kw in keywords)


class RAGEvaluator:
    """RAG 检索质量评测器 —— 支持 chunk 级 + 文档级评测。"""

    def __init__(self, vector_store: VectorStoreService | None = None):
        self.vector_store = vector_store or VectorStoreService()
        self._reranker = None

    @property
    def _rerank(self):
        if self._reranker is None:
            from app.rag.reranker import reranker
            self._reranker = reranker
        return self._reranker

    def _retrieve(self, query: str, k: int, use_rerank: bool = True):
        """统一检索入口：宽召回 + 可选精排。"""
        if use_rerank:
            wide_retriever = self.vector_store.get_retriever(k=10)
            candidates = wide_retriever.invoke(query)
            return self._rerank.rerank(query, candidates, top_n=k)
        retriever = self.vector_store.get_retriever(k=k)
        return retriever.invoke(query)[:k]

    # ── chunk 级指标（按内容关键词匹配）───────────────────────────

    def precision_at_k(
        self, query: str, relevant_keywords: list[str], k: int | None = None
    ) -> float:
        """Precision@K: 检索到的 top-K chunk 中,内容命中关键词的比例。"""
        k = k or settings.chroma_k
        if not relevant_keywords:
            return 0.0
        retrieved = self._retrieve(query, k)
        if not retrieved:
            return 0.0
        hits = sum(1 for doc in retrieved if _chunk_matches(doc, relevant_keywords))
        return hits / len(retrieved)

    def mrr_at_k_chunks(
        self, query: str, relevant_keywords: list[str], k: int | None = None
    ) -> float:
        """chunk 级 MRR@K: 第一个命中关键词的 chunk 的排名的倒数。"""
        k = k or settings.chroma_k
        if not relevant_keywords:
            return 0.0
        retrieved = self._retrieve(query, k)
        for rank, doc in enumerate(retrieved, 1):
            if _chunk_matches(doc, relevant_keywords):
                return 1.0 / rank
        return 0.0

    def hit_at_k_chunks(
        self, query: str, relevant_keywords: list[str], k: int | None = None
    ) -> float:
        """chunk 级 Hit@K: top-K 中是否至少命中一个关键词。"""
        k = k or settings.chroma_k
        if not relevant_keywords:
            return 0.0
        retrieved = self._retrieve(query, k)
        return 1.0 if any(_chunk_matches(doc, relevant_keywords) for doc in retrieved) else 0.0

    # ── 文档级指标（按 source 文件名匹配）─────────────────────────

    def recall_at_k(
        self, query: str, relevant_doc_ids: set[str], k: int | None = None
    ) -> float:
        """Recall@K: 检索结果中相关文档占全部相关文档的比例。"""
        k = k or settings.chroma_k
        retrieved = self._retrieve(query, k)
        retrieved_ids = {_source_key(doc) for doc in retrieved}
        if not relevant_doc_ids:
            return 0.0
        return len(retrieved_ids & relevant_doc_ids) / len(relevant_doc_ids)

    def hit_rate(
        self, query: str, relevant_doc_ids: set[str], k: int | None = None
    ) -> float:
        """Hit Rate@K: 检索结果中至少命中一个相关文档的比例（0 或 1）。"""
        k = k or settings.chroma_k
        retrieved = self._retrieve(query, k)
        retrieved_ids = {_source_key(doc) for doc in retrieved}
        return 1.0 if (retrieved_ids & relevant_doc_ids) else 0.0

    def mrr(self, query: str, relevant_doc_ids: set[str], k: int | None = None) -> float:
        """MRR@K: 第一个相关文档的排名的倒数。"""
        k = k or settings.chroma_k
        retrieved = self._retrieve(query, k)
        for rank, doc in enumerate(retrieved, 1):
            if _source_key(doc) in relevant_doc_ids:
                return 1.0 / rank
        return 0.0

    # ── 源多样性检查 ───────────────────────────────────────────────

    def source_diversity(self) -> dict:
        """返回向量库中的唯一 source 数和文档总数,用于评估评测可信度。"""
        try:
            all_data = self.vector_store.vector_store.get()
            sources = set()
            for meta in (all_data.get("metadatas") or []):
                src = meta.get("source", "")
                if src:
                    sources.add(os.path.basename(src))
            return {
                "total_chunks": len(all_data.get("ids") or []),
                "unique_sources": len(sources),
                "source_names": sorted(sources),
            }
        except Exception:
            return {"total_chunks": 0, "unique_sources": 0, "source_names": []}

    # ── 批量评测 ───────────────────────────────────────────────────

    def evaluate(
        self,
        test_cases: list[dict],
        k: int | None = None,
    ) -> dict:
        """批量评测。

        test_cases 格式:
        [
            {
                "query": "...",
                "relevant_keywords": ["定期清理", "滤网"],   # chunk 级: 内容关键词
                "relevant_docs": {"guide.txt"}               # 文档级: 期望文件名 (可选)
            },
            ...
        ]
        """
        k = k or settings.chroma_k
        precisions, chunk_mrrs, chunk_hits = [], [], []
        recalls, doc_hits, doc_mrrs = [], [], []

        for case in test_cases:
            query = case["query"]
            keywords = case.get("relevant_keywords", [])
            relevant_docs = set(case.get("relevant_docs", []))

            # 每个 query 只检索一次，复用给所有指标
            retrieved = self._retrieve(query, k)

            # chunk 级
            if keywords and retrieved:
                hits = sum(1 for doc in retrieved if _chunk_matches(doc, keywords))
                precisions.append(hits / len(retrieved))

                mrr_val = 0.0
                for rank, doc in enumerate(retrieved, 1):
                    if _chunk_matches(doc, keywords):
                        mrr_val = 1.0 / rank
                        break
                chunk_mrrs.append(mrr_val)
                chunk_hits.append(1.0 if hits > 0 else 0.0)

            # 文档级
            if relevant_docs and retrieved:
                retrieved_ids = {_source_key(doc) for doc in retrieved}
                recalls.append(len(retrieved_ids & relevant_docs) / len(relevant_docs))
                doc_hits.append(1.0 if (retrieved_ids & relevant_docs) else 0.0)

                mrr_val = 0.0
                for rank, doc in enumerate(retrieved, 1):
                    if _source_key(doc) in relevant_docs:
                        mrr_val = 1.0 / rank
                        break
                doc_mrrs.append(mrr_val)

        n_chunk = len(precisions)
        n_doc = len(recalls)
        diversity = self.source_diversity()

        return {
            "k": k,
            "num_queries": len(test_cases),
            # chunk 级指标
            "precision_at_k": round(sum(precisions) / n_chunk, 4) if n_chunk else None,
            "chunk_mrr": round(sum(chunk_mrrs) / n_chunk, 4) if n_chunk else None,
            "chunk_hit_rate": round(sum(chunk_hits) / n_chunk, 4) if n_chunk else None,
            "num_with_chunk_labels": n_chunk,
            # 文档级指标
            "recall_at_k": round(sum(recalls) / n_doc, 4) if n_doc else None,
            "doc_hit_rate": round(sum(doc_hits) / n_doc, 4) if n_doc else None,
            "doc_mrr": round(sum(doc_mrrs) / n_doc, 4) if n_doc else None,
            "num_with_doc_labels": n_doc,
            # 源多样性
            "source_diversity": diversity,
        }

    # ── LLM-as-Judge 评测 ─────────────────────────────────────────

    _JUDGE_PROMPT = """你是一个检索质量评估员。你的任务是判断：仅凭以下参考资料，是否足以回答用户的问题。

用户问题：{query}

参考资料：
{chunks}

判断规则：
- 如果参考资料中包含问题的直接答案或足够的相关信息，回复 YES
- 如果参考资料与问题无关、信息不足、或只能部分回答，回复 NO
- 只回复 YES 或 NO，不要解释"""

    def _build_judge_prompt(self, query: str, docs: list) -> str:
        chunks = "\n\n".join(
            f"【资料{i}】：{doc.page_content}" for i, doc in enumerate(docs, 1)
        )
        return self._JUDGE_PROMPT.format(query=query, chunks=chunks)

    def judge_single(self, query: str, k: int | None = None) -> tuple[bool, float]:
        """LLM 判断检索结果是否能回答 query。返回 (是否相关, 耗时ms)。"""
        from app.model.factory import chat_model

        k = k or settings.chroma_k
        t0 = time.perf_counter()
        retrieved = self._retrieve(query, k)
        prompt = self._build_judge_prompt(query, retrieved)

        try:
            result = chat_model.invoke(prompt).content.strip().upper()
            elapsed = (time.perf_counter() - t0) * 1000
            return result.startswith("YES"), elapsed
        except Exception as e:
            logger.error("[LLM-Judge] 评测失败: %s", e)
            elapsed = (time.perf_counter() - t0) * 1000
            return False, elapsed

    def evaluate_llm_judge(self, test_cases: list[dict], k: int | None = None) -> dict:
        """批量 LLM-as-Judge 评测。返回 LLM Precision 和各条详情。"""
        k = k or settings.chroma_k
        results = []
        for case in test_cases:
            query = case["query"]
            ok, elapsed_ms = self.judge_single(query, k)
            results.append({
                "query": query,
                "relevant": ok,
                "elapsed_ms": round(elapsed_ms, 0),
            })
            logger.info("[LLM-Judge] %s -> %s (%.0fms)", query, "YES" if ok else "NO", elapsed_ms)

        yes_count = sum(1 for r in results if r["relevant"])
        return {
            "llm_precision": round(yes_count / len(results), 4) if results else 0,
            "num_queries": len(results),
            "yes_count": yes_count,
            "no_count": len(results) - yes_count,
            "details": results,
        }


class LLMCache:
    """LLM 结果缓存 —— 基于 query + model 的哈希缓存，减少重复调用。"""

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._hits = 0
        self._misses = 0
        self._hit_times: list[float] = []   # 命中时的查询耗时 (ms)
        self._miss_times: list[float] = []  # 未命中时的查询耗时 (ms)
        self._recent_events: list[dict] = []  # 最近 50 条缓存事件

    @staticmethod
    def _cache_key(query: str, prefix: str = "") -> str:
        raw = f"{prefix}:{query}:{settings.LLM_MODEL}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, query: str, prefix: str = "") -> str | None:
        key = self._cache_key(query, prefix)
        entry = self._cache.get(key)
        if entry and time.time() - entry["ts"] < 3600:
            self._hits += 1
            return entry["value"]
        self._misses += 1
        return None

    def set(self, query: str, value: str, prefix: str = ""):
        key = self._cache_key(query, prefix)
        self._cache[key] = {"value": value, "ts": time.time()}

    def record(self, hit: bool, elapsed_ms: float, query: str, prefix: str = ""):
        """记录一次缓存事件（含耗时），供监控面板使用。"""
        if hit:
            self._hit_times.append(elapsed_ms)
        else:
            self._miss_times.append(elapsed_ms)
        self._recent_events.append({
            "ts": time.strftime("%H:%M:%S"),
            "hit": hit,
            "elapsed_ms": round(elapsed_ms, 1),
            "query": query[:80],
            "prefix": prefix,
        })
        if len(self._recent_events) > 50:
            self._recent_events = self._recent_events[-50:]

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return round(self._hits / total, 4) if total else 0.0

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        avg_hit = round(sum(self._hit_times) / len(self._hit_times), 1) if self._hit_times else 0
        avg_miss = round(sum(self._miss_times) / len(self._miss_times), 1) if self._miss_times else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": self.hit_rate,
            "cache_entries": len(self._cache),
            "avg_hit_ms": avg_hit,
            "avg_miss_ms": avg_miss,
            "recent_events": self._recent_events[-20:],
        }


# 全局缓存实例
llm_cache = LLMCache()
