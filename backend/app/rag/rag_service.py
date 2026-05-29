from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.model.factory import chat_model
from app.rag.evaluation import llm_cache
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
        cached = llm_cache.get(query, prefix="rag")
        if cached:
            logger.info("[RAG] 命中缓存，跳过 LLM 调用")
            return cached

        context_docs = self.retrieve_docs(query)
        context = ""
        for i, doc in enumerate(context_docs, 1):
            context += f"【参考资料{i}】：{doc.page_content} | 元数据：{doc.metadata}\n"

        result = self.chain.invoke({"input": query, "context": context})
        llm_cache.set(query, result, prefix="rag")
        return result


if __name__ == "__main__":
    vs = VectorStoreService()
    rag = RagSummarizeService(vs)
    print(rag.rag_summarize("小户型适合哪种扫地机器人？"))