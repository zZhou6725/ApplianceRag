import re

from app.utils.logger_handler import logger


class ToolRouter:
    INTENT_SKILL_MAP = {
        "consultation": "rag",
        "weather": "weather",
        "report": "report",
        "user_info": "user",
    }

    REPORT_KEYWORDS = ["报告", "月度", "使用情况", "月报", "总结", "生成报告"]
    WEATHER_KEYWORDS = ["天气", "气温", "下雨", "刮风", "温度", "晴天", "阴天", "湿度"]
    USER_KEYWORDS = ["我的", "账户", "记录", "数据", "用户", "使用记录"]

    @staticmethod
    def classify_intent(query: str) -> str:
        for kw in ToolRouter.REPORT_KEYWORDS:
            if kw in query:
                return "report"
        for kw in ToolRouter.WEATHER_KEYWORDS:
            if kw in query:
                return "weather"
        for kw in ToolRouter.USER_KEYWORDS:
            if kw in query:
                return "user_info"
        return "consultation"

    @staticmethod
    def route(intent: str):
        from skills.base import SKILL_REGISTRY

        skill_name = ToolRouter.INTENT_SKILL_MAP.get(intent)
        if skill_name is None:
            logger.warning(f"[ToolRouter] 未知意图 {intent}，回退到 rag")
            skill_name = "rag"

        skill = SKILL_REGISTRY.get(skill_name)
        if skill is None:
            logger.warning(f"[ToolRouter] 技能 {skill_name} 未注册")
        return skill

    @staticmethod
    def validate_params(skill, query: str, context: dict) -> bool:
        if skill is None:
            return False
        return skill.validate_input(query, context)
