"""Runtime context and tool wrappers for the agent."""

from dataclasses import dataclass, field
from functools import wraps

from app.utils.logger_handler import logger


@dataclass
class AgentContext:
    report: bool = False


# Module-level shared context — tools and prompt functions read/write this
_ctx: AgentContext = AgentContext()


def get_context() -> AgentContext:
    return _ctx


def reset_context() -> None:
    _ctx.report = False


def monitored_tool(func):
    """Decorator that logs tool calls and handles context injection."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = getattr(func, "name", func.__name__)
        logger.info(f"[tool] 执行工具: {tool_name}")
        if args:
            logger.info(f"[tool] 参数: {args[0][:200] if isinstance(args[0], str) else args[0]}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"[tool] 工具 {tool_name} 调用成功")

            if tool_name == "fill_context_for_report":
                logger.info("[tool] fill_context_for_report 被调用，设置 report=True")
                _ctx.report = True

            return result
        except Exception as e:
            logger.error(f"[tool] 工具 {tool_name} 调用失败: {e}")
            raise

    return wrapper
