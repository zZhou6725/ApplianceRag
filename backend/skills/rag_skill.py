from .base import BaseSkill, SkillResult, SKILL_REGISTRY


class RAGSkill(BaseSkill):
    name = "rag"
    description = "从产品知识库检索答案，处理产品咨询、故障排查、保养等问题"

    def validate_input(self, query: str, context: dict) -> bool:
        return bool(query and query.strip())

    def execute(self, query: str, context: dict) -> SkillResult:
        from app.agent.tools.agent_tools import rag_summarize

        output = rag_summarize.invoke({"query": query})
        return SkillResult(skill_name=self.name, output=output)


SKILL_REGISTRY["rag"] = RAGSkill()
