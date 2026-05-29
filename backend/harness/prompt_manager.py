from functools import lru_cache

from app.core.config import settings
from app.utils.path_tools import get_abs_path


class PromptManager:
    _TEMPLATE_PATHS = {
        "system": settings.main_prompt_path,
        "report": settings.report_prompt_path,
        "rag_summarize": settings.rag_summarize_prompt_path,
    }

    @staticmethod
    @lru_cache(maxsize=8)
    def load_template(name: str) -> str:
        path = get_abs_path(PromptManager._TEMPLATE_PATHS.get(name, PromptManager._TEMPLATE_PATHS["system"]))
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def render(template: str, variables: dict) -> str:
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    @staticmethod
    def get_system_prompt(metadata: dict | None = None) -> str:
        if metadata and metadata.get("report_mode"):
            return PromptManager.load_template("report")
        return PromptManager.load_template("system")
