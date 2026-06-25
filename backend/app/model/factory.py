from app.utils.dashscope_patch import apply as _apply_patch
_apply_patch()

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings

from app.core.config import settings
from app.utils.logger_handler import logger

logger.info("[Model] 初始化 ChatTongyi model=%s", settings.rag_chat_model)
chat_model = ChatTongyi(model=settings.rag_chat_model)
logger.info("[Model] 初始化 DashScopeEmbeddings model=%s", settings.rag_embedding_model)
embed_model = DashScopeEmbeddings(model=settings.rag_embedding_model)
embed_model = DashScopeEmbeddings(model=settings.rag_embedding_model)