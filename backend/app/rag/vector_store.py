import os
import shutil

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from app.core.config import settings
from app.model.factory import embed_model
from app.utils.file_handler import (
    csv_loader,
    get_file_md5_hex,
    listdir_with_allowed_type,
    pdf_loader,
    txt_loader,
)
from app.utils.logger_handler import logger
from app.utils.path_tools import get_abs_path


class VectorStoreService:
    def __init__(self):
        persist_dir = str(settings.chroma_dir)
        try:
            self.vector_store = Chroma(
                collection_name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=embed_model,
                persist_directory=persist_dir,
            )
        except Exception:
            logger.warning("[VectorStore] ChromaDB 初始化失败，正在重建...")
            if os.path.exists(persist_dir):
                shutil.rmtree(persist_dir)
            self.vector_store = Chroma(
                collection_name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=embed_model,
                persist_directory=persist_dir,
            )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chroma_chunk_size,
            chunk_overlap=settings.chroma_chunk_overlap,
            separators=settings.chroma_separators,
            length_function=len,
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": settings.chroma_k})

    def load_document(self):
        md5_store_path = get_abs_path(settings.chroma_md5_store)

        def check_md5_hex(md5_for_check: str) -> bool:
            if not os.path.exists(md5_store_path):
                open(md5_store_path, "w", encoding="utf-8").close()
                return False
            with open(md5_store_path, "r", encoding="utf-8") as f:
                return any(line.strip() == md5_for_check for line in f)

        def save_md5_hex(md5_for_save: str):
            with open(md5_store_path, "a", encoding="utf-8") as f:
                f.write(md5_for_save + "\n")

        def get_file_documents(read_path: str) -> list[Document]:
            if read_path.endswith(".txt"):
                return txt_loader(read_path)
            elif read_path.endswith(".pdf"):
                return pdf_loader(read_path)
            elif read_path.endswith(".csv"):
                return csv_loader(read_path)
            return []

        allowed_files = listdir_with_allowed_type(
            get_abs_path(settings.chroma_data_path),
            tuple(settings.chroma_allow_file_types),
        )

        for path in allowed_files:
            md5_hex = get_file_md5_hex(path)
            if not md5_hex:
                logger.warning(f"[加载知识库] {path} MD5计算失败，跳过")
                continue
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库] {path} 已存在，跳过")
                continue

            try:
                documents = get_file_documents(path)
                if not documents:
                    logger.warning(f"[加载知识库] {path} 无有效内容，跳过")
                    continue

                split_docs = self.splitter.split_documents(documents)
                if not split_docs:
                    logger.warning(f"[加载知识库] {path} 分片后无内容，跳过")
                    continue

                self.vector_store.add_documents(split_docs)
                save_md5_hex(md5_hex)
                logger.info(f"[加载知识库] {path} 加载成功")
            except Exception as e:
                logger.error(f"[加载知识库] {path} 加载失败：{e}", exc_info=True)


if __name__ == "__main__":
    store = VectorStoreService()
    store.load_document()
    retriever = store.get_retriever()
    for r in retriever.invoke("迷路"):
        print(r.page_content)
        print("-" * 20)