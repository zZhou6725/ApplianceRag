import hashlib
import os

from langchain_community.document_loaders import CSVLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document


def get_file_md5_hex(filepath: str) -> str | None:
    """计算文件 MD5 哈希值（分片读取，支持大文件）。"""
    if not os.path.isfile(filepath):
        return None

    md5_obj = hashlib.md5()
    chunk_size = 4096
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)
        return md5_obj.hexdigest()
    except (PermissionError, OSError):
        return None


def listdir_with_allowed_type(path: str, allowed_types: tuple[str, ...]) -> list[str]:
    """列出目录下所有指定后缀的文件。"""
    files: list[str] = []
    if not os.path.isdir(path):
        return files

    for f in os.listdir(path):
        if f.endswith(allowed_types):
            files.append(os.path.join(path, f))
    return files


def csv_loader(
    filepath: str, source_column: str | None = None, encoding: str = "utf-8",
    csv_args: dict | None = None,
) -> list[Document]:
    return CSVLoader(filepath, source_column=source_column, encoding=encoding, csv_args=csv_args).load()


def pdf_loader(filepath: str, password: str | None = None) -> list[Document]:
    return PyPDFLoader(filepath, password=password).load()


def txt_loader(filepath: str) -> list[Document]:
    return TextLoader(filepath, encoding="utf-8").load()