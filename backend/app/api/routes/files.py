"""文件上传接口 —— 支持 Word/PDF/TXT/图片，提取文本用于对话上下文。"""
from fastapi import APIRouter, File, UploadFile

from app.core.response import success
from app.utils.file_parser import parse_file
from app.utils.logger_handler import logger

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    logger.info(f"[上传] 收到文件: {file.filename}, 大小: {file.size}")

    try:
        content = file.file.read()
    except Exception:
        return success(data=None, message="文件读取失败")

    if not content:
        return success(data=None, message="文件内容为空")

    try:
        text = parse_file(content, file.filename or "unknown")
    except ValueError as e:
        return success(data=None, message=str(e))
    except Exception as e:
        logger.error(f"[上传] 解析失败: {e}")
        return success(data=None, message=f"文件解析失败: {e}")

    # 截断过长内容，保留前 8000 字
    preview = text[:400] + ("..." if len(text) > 400 else "")
    full = text[:8000]

    return success(data={
        "filename": file.filename,
        "file_size": len(content),
        "preview": preview,
        "content": full,
        "char_count": len(text),
    })