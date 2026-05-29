from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from graph.nodes import (
    assemble_result_node,
    classify_intent_node,
    dispatch_skill_node,
    generate_output_node,
    recall_memory_node,
    store_memory_node,
)
from graph.state import AgentState, create_initial_state


def _route_after_classify(state: AgentState) -> str:
    return "generate_output" if state.get("intent") == "general" else "dispatch_skill"


def _route_after_assemble(state: AgentState) -> str:
    if state.get("final_answer"):
        return "generate_output"
    if state.get("error_count", 0) >= 3:
        return "generate_output"
    results = state.get("skill_results", [])
    if results and results[-1].get("error"):
        return "dispatch_skill"
    return "generate_output"


class AgentGraph:
    def __init__(self, enable_memory: bool = True):
        self._enable_memory = enable_memory
        self._graph = self._build()

    def _build(self) -> CompiledStateGraph:
        builder = StateGraph(AgentState)

        builder.add_node("recall_memory", recall_memory_node)
        builder.add_node("classify_intent", classify_intent_node)
        builder.add_node("dispatch_skill", dispatch_skill_node)
        builder.add_node("assemble_result", assemble_result_node)
        builder.add_node("generate_output", generate_output_node)
        builder.add_node("store_memory", store_memory_node)

        if self._enable_memory:
            builder.add_edge(START, "recall_memory")
            builder.add_edge("recall_memory", "classify_intent")
        else:
            builder.add_edge(START, "classify_intent")

        builder.add_conditional_edges("classify_intent", _route_after_classify, {
            "dispatch_skill": "dispatch_skill",
            "generate_output": "generate_output",
        })
        builder.add_edge("dispatch_skill", "assemble_result")
        builder.add_conditional_edges("assemble_result", _route_after_assemble, {
            "dispatch_skill": "dispatch_skill",
            "generate_output": "generate_output",
        })

        if self._enable_memory:
            builder.add_edge("generate_output", "store_memory")
            builder.add_edge("store_memory", END)
        else:
            builder.add_edge("generate_output", END)

        return builder.compile()

    def run(self, query: str, history: list | None = None) -> AgentState:
        """Non-streaming execution. Returns final state with final_answer set."""
        initial = create_initial_state(query, history)
        return self._graph.invoke(initial)

    def stream(self, query: str, history: list | None = None):
        """Sync generator: step through graph, then stream LLM tokens."""
        from langchain_core.messages import AIMessage

        from app.model.factory import chat_model
        from harness.context_builder import ContextBuilder
        from harness.prompt_manager import PromptManager

        state = create_initial_state(query, history)

        # Step 0: recall memory
        if self._enable_memory:
            mem_result = recall_memory_node(state)
            state.update(mem_result)

        # Step 1: classify intent
        intent_result = classify_intent_node(state)
        state.update(intent_result)

        # Step 2: dispatch skill (skip for general)
        if state["intent"] != "general":
            skill_result = dispatch_skill_node(state)
            state.update(skill_result)

        # Step 3: assemble / validate
        assembled = assemble_result_node(state)
        state.update(assembled)

        # Step 4: generate output
        if state.get("final_answer"):
            yield state["final_answer"]
        else:
            metadata = state.get("metadata", {})
            memory_ctx = metadata.get("memory_context", "")
            system_prompt = PromptManager.get_system_prompt(metadata)
            if memory_ctx:
                system_prompt = memory_ctx + "\n\n" + system_prompt

            messages = ContextBuilder.build_messages(
                query=state["query"],
                history=state.get("messages", []),
                system_prompt=system_prompt,
                skill_results=state.get("skill_results"),
            )

            full = ""
            for chunk in chat_model.stream(messages):
                if chunk.content:
                    full += chunk.content
                    yield chunk.content

            state["final_answer"] = full

        state["messages"] = state.get("messages", []) + [AIMessage(content=state.get("final_answer", ""))]

        # Step 5: store memory
        if self._enable_memory and state.get("final_answer"):
            store_memory_node(state)
