import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    skill_name: str
    output: Any = None
    error: str | None = None
    elapsed_ms: float = 0.0
    retries: int = 0


class BaseSkill(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def validate_input(self, query: str, context: dict) -> bool:
        ...

    @abstractmethod
    def execute(self, query: str, context: dict) -> SkillResult:
        ...

    def validate_output(self, result: SkillResult) -> bool:
        if result is None:
            return False
        if result.error:
            return False
        if result.output is None:
            return False
        if isinstance(result.output, str) and not result.output.strip():
            return False
        return True

    def run(self, query: str, context: dict) -> SkillResult:
        if not self.validate_input(query, context):
            return SkillResult(
                skill_name=self.name, output=None,
                error=f"[{self.name}] 输入校验失败",
            )
        t0 = time.perf_counter()
        try:
            result = self.execute(query, context)
        except Exception as e:
            return SkillResult(
                skill_name=self.name, output=None,
                error=str(e),
                elapsed_ms=(time.perf_counter() - t0) * 1000,
            )
        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        if not self.validate_output(result):
            result.error = result.error or f"[{self.name}] 输出校验失败"
        return result


SKILL_REGISTRY: dict[str, BaseSkill] = {}
