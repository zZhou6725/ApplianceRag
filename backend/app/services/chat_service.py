import json

from sqlalchemy.orm import Session

from app.agent.react_agent import ReactAgent
from app.services.conversation_service import add_message, create_conversation
from app.utils.logger_handler import logger

_agent: ReactAgent | None = None


def _get_agent() -> ReactAgent:
    global _agent
    if _agent is None:
        _agent = ReactAgent()
    return _agent


def _build_query(message: str, file_context: str | None, file_name: str | None) -> str:
    """将文件内容 + 用户消息组装为 Agent 查询。"""
    if not file_context:
        return message

    parts = ["以下是用户上传文件的内容，请基于此内容回答用户问题："]
    if file_name:
        parts.append(f"文件名称：{file_name}")
    parts.append(f"\n--- 文件内容开始 ---\n{file_context}\n--- 文件内容结束 ---\n")
    parts.append(f"用户问题：{message}")
    return "\n".join(parts)


async def stream_chat(
    db: Session,
    conversation_id: str | None,
    message: str,
    file_context: str | None = None,
    file_name: str | None = None,
):
    """SSE streaming generator for agent chat."""
    if not conversation_id:
        conversation_id = create_conversation(db)
        logger.info("[Chat] 创建新对话: %s", conversation_id)
    else:
        logger.info("[Chat] 使用已有对话: %s", conversation_id)

    # 用户消息存入数据库时保留原始文本 + 文件信息
    display_message = message
    if file_name:
        display_message = f"[上传文件: {file_name}]\n{message}"
    add_message(db, conversation_id, "user", display_message)
    logger.info("[Chat] 用户消息: %s", display_message[:200])

    try:
        agent = _get_agent()
        query = _build_query(message, file_context, file_name)
        accumulated = ""
        chunk_count = 0

        for chunk in agent.execute_stream(query):
            accumulated += chunk
            chunk_count += 1
            yield f"event: token\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

        logger.info("[Chat] 流式完成, 共 %d chunks, 总长度 %d", chunk_count, len(accumulated))
        add_message(db, conversation_id, "assistant", accumulated.strip())

        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error("[Chat] 异常: %s", e)
        yield f"event: error\ndata: {json.dumps({'detail': str(e)}, ensure_ascii=False)}\n\n"