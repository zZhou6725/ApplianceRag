from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings

from app.core.config import settings

chat_model = ChatTongyi(model=settings.rag_chat_model)
embed_model = DashScopeEmbeddings(model=settings.rag_embedding_model)