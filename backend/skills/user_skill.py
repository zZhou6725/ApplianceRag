from .base import BaseSkill, SkillResult, SKILL_REGISTRY


class UserSkill(BaseSkill):
    name = "user"
    description = "获取用户ID、当前月份和使用记录数据"

    def validate_input(self, query: str, context: dict) -> bool:
        return bool(query and query.strip())

    def execute(self, query: str, context: dict) -> SkillResult:
        from app.agent.tools.agent_tools import (
            fetch_external_data,
            get_current_month,
            get_user_id,
        )

        user_id = get_user_id.invoke({})
        month = get_current_month.invoke({})
        usage = fetch_external_data.invoke({"user_id": user_id, "month": month})
        return SkillResult(
            skill_name=self.name,
            output={"user_id": user_id, "month": month, "usage_data": usage},
        )


SKILL_REGISTRY["user"] = UserSkill()
