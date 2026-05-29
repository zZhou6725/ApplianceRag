"""文件解析器 —— 从 Word/PDF/TXT/图片 中提取文本。"""
import io
import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from docx import Document as DocxDocument


MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".png", ".jpg", ".jpeg"}
TEXT_EXTENSIONS = {".txt", ".md"}


def parse_file(file_bytes: bytes, filename: str) -> str:
    """根据文件后缀解析文本内容，返回提取的纯文本。"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}")

    if len(file_bytes) > MAX_FILE_BYTES:
        raise ValueError(f"文件过大，最大支持 10MB")

    if ext in TEXT_EXTENSIONS:
        return file_bytes.decode("utf-8", errors="replace")

    if ext == ".pdf":
        return _parse_pdf(file_bytes, filename)

    if ext == ".docx":
        return _parse_docx(file_bytes)

    if ext in (".png", ".jpg", ".jpeg"):
        return _parse_image(file_bytes, filename)

    raise ValueError(f"未实现的解析器: {ext}")


def _parse_pdf(file_bytes: bytes, filename: str) -> str:
    """从 PDF 字节流提取文本（写入临时文件供 PyPDFLoader 读取）。"""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(file_bytes)
        tmp.close()
        docs = PyPDFLoader(tmp.name).load()
        return "\n\n".join(d.page_content for d in docs if d.page_content).strip()
    finally:
        os.unlink(tmp.name)


def _parse_docx(file_bytes: bytes) -> str:
    """从 DOCX 字节流提取文本。"""
    doc = DocxDocument(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _parse_image(file_bytes: bytes, filename: str) -> str:
    """图片说明（OCR 需额外部署 Tesseract/PaddleOCR，此处保留扩展接口）。"""
    from PIL import Image
    img = Image.open(io.BytesIO(file_bytes))
    w, h = img.size
    return (
        f"[图片文件: {filename}]\n"
        f"尺寸: {w}×{h} 像素\n"
        f"大小: {len(file_bytes) // 1024}KB\n"
        f"(如需 OCR 识别图中文字，请部署 Tesseract 或 PaddleOCR)"
    )