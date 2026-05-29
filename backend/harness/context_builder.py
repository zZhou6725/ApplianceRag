import json
import threading
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


MAX_HISTORY_TURNS = 10


class ContextBuilder:

    @staticmethod
    def build_messages(
        query: str,
        history: list[BaseMessage],
        system_prompt: str,
        skill_results: list[dict] | None = None,
    ) -> list[BaseMessage]:
        messages = [SystemMessage(content=system_prompt)]

        max_msgs = MAX_HISTORY_TURNS * 2
        if history:
            messages.extend(history[-max_msgs:])

        if skill_results:
            context_text = ContextBuilder._format_skill_results(skill_results)
            messages.append(HumanMessage(
                content=f"[系统检索结果]\n{context_text}\n\n用户问题：{query}"
            ))
        else:
            messages.append(HumanMessage(content=query))

        return messages

    @staticmethod
    def build_context(state: dict) -> dict:
        return {
            "report_mode": state.get("metadata", {}).get("report_mode", False),
            "messages": state.get("messages", []),
            "query": state["query"],
        }

    @staticmethod
    def _format_skill_results(results: list[dict]) -> str:
        parts = []
        for r in results:
            name = r.get("skill_name", "unknown")
            if r.get("error"):
                parts.append(f"[{name}] 出错: {r['error']}")
            else:
                output = r.get("output", "")
                if isinstance(output, dict):
                    output = json.dumps(output, ensure_ascii=False, indent=2)
                parts.append(f"[{name}]\n{output}")
        return "\n\n".join(parts)


class ConversationState:
    def __init__(self):
        self._messages: list[BaseMessage] = []
        self._lock = threading.Lock()
        self._user_context: dict[str, Any] = {}

    def add_message(self, role: str, content: str) -> None:
        with self._lock:
            if role == "user":
                self._messages.append(HumanMessage(content=content))
            else:
                self._messages.append(AIMessage(content=content))

    def get_history(self) -> list[BaseMessage]:
        with self._lock:
            return list(self._messages)

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()
            self._user_context.clear()

    def set_context(self, key: str, value: Any) -> None:
        with self._lock:
            self._user_context[key] = value

    def get_context(self, key: str) -> Any:
        with self._lock:
            return self._user_context.get(key)
