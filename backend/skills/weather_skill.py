import re

from .base import BaseSkill, SkillResult, SKILL_REGISTRY


class WeatherSkill(BaseSkill):
    name = "weather"
    description = "获取天气信息，自动定位城市后查询天气"

    def validate_input(self, query: str, context: dict) -> bool:
        return bool(query and query.strip())

    def execute(self, query: str, context: dict) -> SkillResult:
        from app.agent.tools.agent_tools import get_user_location, get_weather

        city = context.get("city", "")
        if not city:
            city_match = re.search(r"(\w{2,4})(?:的)?天气", query)
            if city_match:
                city = city_match.group(1)

        if not city:
            location_result = get_user_location.invoke({})
            city = location_result if location_result else "深圳"

        weather = get_weather.invoke({"city": city})
        return SkillResult(skill_name=self.name, output={"city": city, "weather": weather})


SKILL_REGISTRY["weather"] = WeatherSkill()
