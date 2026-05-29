import asyncio
import random
from typing import Any

from app.utils.logger_handler import logger


class ErrorHandler:
    FALLBACK_MESSAGES = [
        "抱歉，我暂时无法回答这个问题，请稍后再试。",
        "服务繁忙，请稍等片刻再问我。",
        "我遇到了一个技术问题，请换一种方式问我。",
    ]

    @staticmethod
    async def safe_execute(coro_func, *args, timeout: float = 30.0, fallback: str | None = None, **kwargs) -> Any:
        try:
            return await asyncio.wait_for(coro_func(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"[ErrorHandler] 操作超时 ({timeout}s)")
            return fallback or random.choice(ErrorHandler.FALLBACK_MESSAGES)
        except Exception as e:
            logger.error(f"[ErrorHandler] 执行异常: {e}", exc_info=True)
            return fallback or random.choice(ErrorHandler.FALLBACK_MESSAGES)

    @staticmethod
    def safe_sync_execute(func, *args, timeout: float = 30.0, fallback: str | None = None, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[ErrorHandler] 同步执行异常: {e}", exc_info=True)
            return fallback or random.choice(ErrorHandler.FALLBACK_MESSAGES)
