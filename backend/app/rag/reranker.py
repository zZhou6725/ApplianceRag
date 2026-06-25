"""基于 DashScope gte-rerank-v2 的重排序服务。

召回-精排流水线：
1. 向量检索召回 top-10 候选文档
2. Rerank 精排取 top-n
"""
import time

from curl_cffi import requests as http
from langchain_core.documents import Document

from app.core.config import settings
from app.utils.logger_handler import logger

RERANK_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
RERANK_MODEL = "gte-rerank-v2"


class Reranker:
    def __init__(self, model: str = RERANK_MODEL):
        self._model = model
        self._api_key = settings.DASHSCOPE_API_KEY
        self._hit_count = 0
        self._miss_count = 0

    def rerank(
        self,
        query: str,
        documents: list[Document],
        top_n: int = 3,
    ) -> list[Document]:
        """对候选文档重排序，返回 top_n 最相关文档。"""
        if not documents:
            return []
        if len(documents) <= top_n:
            return documents

        t0 = time.perf_counter()
        doc_texts = [doc.page_content for doc in documents]

        try:
            resp = http.post(
                RERANK_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "input": {
                        "query": query,
                        "documents": doc_texts,
                    },
                    "parameters": {
                        "top_n": top_n,
                        "return_documents": False,
                    },
                },
                timeout=10,
            )
            data = resp.json()

            if "output" not in data:
                logger.warning("[Reranker] API 异常: %s", data.get("message", ""))
                self._miss_count += 1
                return documents[:top_n]  # 降级：返回原始 top_n

            results = sorted(
                data["output"]["results"],
                key=lambda x: x["index"],
            )
            reranked = [documents[r["index"]] for r in results]

            elapsed = (time.perf_counter() - t0) * 1000
            self._hit_count += 1
            logger.info(
                "[Reranker] %d 候选 → %d 精选, %.0fms",
                len(documents), len(reranked), elapsed,
            )
            return reranked

        except Exception as e:
            logger.error("[Reranker] 请求失败: %s", e)
            self._miss_count += 1
            return documents[:top_n]  # 降级

    @property
    def stats(self) -> dict:
        total = self._hit_count + self._miss_count
        return {
            "rerank_calls": total,
            "rerank_success": self._hit_count,
            "rerank_fail": self._miss_count,
        }


reranker = Reranker()