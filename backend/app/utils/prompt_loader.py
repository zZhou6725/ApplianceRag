from app.core.config import settings
from app.utils.path_tools import get_abs_path
from app.utils.logger_handler import logger


def load_system_prompt() -> str:
    path = get_abs_path(settings.main_prompt_path)
    try:
        return open(path, "r", encoding="utf-8").read()
    except FileNotFoundError:
        logger.error(f"系统提示词文件不存在: {path}")
        raise
    except Exception as e:
        logger.error(f"读取系统提示词失败: {e}")
        raise


def load_report_prompt() -> str:
    path = get_abs_path(settings.report_prompt_path)
    try:
        return open(path, "r", encoding="utf-8").read()
    except FileNotFoundError:
        logger.error(f"报告提示词文件不存在: {path}")
        raise
    except Exception as e:
        logger.error(f"读取报告提示词失败: {e}")
        raise