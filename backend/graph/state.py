from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    intent: str
    skill_results: list[dict[str, Any]]
    final_answer: str
    error_count: int
    metadata: dict[str, Any]


def create_initial_state(query: str, history: list[BaseMessage] | None = None) -> AgentState:
    return AgentState(
        messages=list(history) if history else [],
        query=query,
        intent="",
        skill_results=[],
        final_answer="",
        error_count=0,
        metadata={},
    )
