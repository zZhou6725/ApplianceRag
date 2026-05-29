from .base import BaseSkill, SkillResult, SKILL_REGISTRY


class ReportSkill(BaseSkill):
    name = "report"
    description = "生成月度使用报告，串联用户数据获取、知识检索、报告生成"

    def validate_input(self, query: str, context: dict) -> bool:
        return bool(query and query.strip())

    def execute(self, query: str, context: dict) -> SkillResult:
        from app.agent.tools.agent_tools import (
            fetch_external_data,
            fill_context_for_report,
            get_current_month,
            get_user_id,
            rag_summarize,
        )

        fill_context_for_report.invoke({})

        user_id = get_user_id.invoke({})
        month = get_current_month.invoke({})
        usage = fetch_external_data.invoke({"user_id": user_id, "month": month})
        advice = rag_summarize.invoke({"query": "扫地机器人月度保养建议和耗材更换"})

        return SkillResult(
            skill_name=self.name,
            output={
                "user_id": user_id,
                "month": month,
                "usage_data": usage,
                "maintenance_advice": advice,
                "report_mode": True,
            },
        )


SKILL_REGISTRY["report"] = ReportSkill()
