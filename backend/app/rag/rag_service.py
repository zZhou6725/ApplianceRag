import time

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.model.factory import chat_model
from harness.cache_manager import cache_manager
from harness.semantic_cache import semantic_cache
from app.rag.reranker import reranker
from app.rag.vector_store import VectorStoreService
from app.utils.logger_handler import logger
from app.utils.path_tools import get_abs_path


class RagSummarizeService:
    _PROMPT_TEXT: str | None = None

    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = self._load_prompt_text()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.chain = self.prompt_template | chat_model | StrOutputParser()

    def _load_prompt_text(self) -> str:
        if self._PROMPT_TEXT is not None:
            return self._PROMPT_TEXT

        path = get_abs_path(settings.rag_summarize_prompt_path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                prompt_text = f.read().strip()
        except Exception as e:
            logger.error(f"读取提示词文件失败: {e}")
            raise

        if not prompt_text:
            raise ValueError(f"提示词文件内容为空: {path}")

        self._PROMPT_TEXT = prompt_text
        return prompt_text

    def retrieve_docs(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)

    def rag_summarize(self, query: str) -> str:
        t0 = time.perf_counter()

        # L1: 语义答案缓存 — 相似问题直接返回
        semantic_answer = semantic_cache.get_answer(query)
        if semantic_answer:
            elapsed = (time.perf_counter() - t0) * 1000
            cache_manager.record(hit=True, elapsed_ms=elapsed, query=query, prefix="semantic")
            logger.info("[RAG] L1语义答案命中 %.1fms", elapsed)
            return semantic_answer

        # L2: 精确哈希缓存 — 完全相同问题
        exact = cache_manager.get(query, prefix="rag")
        if exact:
            elapsed = (time.perf_counter() - t0) * 1000
            cache_manager.record(hit=True, elapsed_ms=elapsed, query=query, prefix="exact")
            logger.info("[RAG] L2精确缓存命中 %.1fms", elapsed)
            return exact

        # L3: 语义文档缓存 — 相似问题复用文档，跳过向量检索
        cached_docs = semantic_cache.get_docs(query)
        if cached_docs:
            context_docs = cached_docs
            logger.info("[RAG] L3语义文档命中，复用 %d 篇文档，跳过向量检索", len(context_docs))
        else:
            # 召回-精排流水线：宽召回 10 篇 → Rerank 精排取 3 篇
            wide_retriever = self.vector_store.get_retriever(k=10)
            candidates = wide_retriever.invoke(query)
            context_docs = reranker.rerank(query, candidates, top_n=3)
            semantic_cache.set_docs(query, context_docs)
            logger.info("[RAG] L3未命中，召回%d篇 → 精排%d篇", len(candidates), len(context_docs))

        context = ""
        for i, doc in enumerate(context_docs, 1):
            context += f"【参考资料{i}】：{doc.page_content} | 元数据：{doc.metadata}\n"

        result = self.chain.invoke({"input": query, "context": context})
        elapsed = (time.perf_counter() - t0) * 1000

        # 存入两层缓存
        cache_manager.set(query, result, prefix="rag")
        semantic_cache.set_answer(query, result)
        cache_manager.record(hit=False, elapsed_ms=elapsed, query=query, prefix="rag")
        logger.info("[RAG] 三层皆未命中，完整RAG耗时 %.1fms", elapsed)
        return result


if __name__ == "__main__":
    vs = VectorStoreService()
    rag = RagSummarizeService(vs)
    print(rag.rag_summarize("小户型适合哪种扫地机器人？"))