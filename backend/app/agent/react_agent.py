import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.tools.agent_tools import (
    fetch_external_data,
    fill_context_for_report,
    get_current_month,
    get_user_id,
    get_user_location,
    get_weather,
    rag_summarize,
)
from app.agent.tools.middleware import get_context, reset_context
from app.model.factory import chat_model
from app.utils.logger_handler import logger
from app.utils.prompt_loader import load_report_prompt, load_system_prompt

ALL_TOOLS = [
    rag_summarize,
    get_weather,
    get_user_location,
    get_user_id,
    get_current_month,
    fetch_external_data,
    fill_context_for_report,
]

TOOL_BY_NAME = {t.name: t for t in ALL_TOOLS}


class ReactAgent:
    def __init__(self):
        self._model = chat_model

    def execute_stream(self, query: str):
        reset_context()

        messages = [
            SystemMessage(content=load_system_prompt()),
            HumanMessage(content=query),
        ]

        model_with_tools = self._model.bind_tools(ALL_TOOLS)
        max_iterations = 10

        for iteration in range(max_iterations):
            if get_context().report:
                current_system = load_report_prompt()
                existing_systems = [m.content for m in messages if isinstance(m, SystemMessage)]
                if current_system not in existing_systems:
                    messages.insert(0, SystemMessage(content=current_system))

            # Stream the model response — accumulate chunks to check for tool_calls
            full_content = ""
            gathered = None  # Final assembled AIMessage

            for chunk in model_with_tools.stream(messages):
                gathered = chunk if gathered is None else gathered + chunk

                # Only yield content if no tool_call_chunks are accumulating
                tc_chunks = getattr(chunk, "tool_call_chunks", None) or []
                if not tc_chunks and chunk.content:
                    yield chunk.content

            messages.append(gathered)

            tool_calls = getattr(gathered, "tool_calls", None) if gathered else None

            if not tool_calls:
                return  # Already streamed the final answer above

            # Execute tools
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                logger.info(f"[Agent] 工具: {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")

                tool_func = TOOL_BY_NAME.get(tool_name)
                if tool_func is None:
                    result = f"错误：未知工具 {tool_name}"
                else:
                    try:
                        result = tool_func.invoke(tool_args)
                    except Exception as e:
                        result = f"工具调用失败：{str(e)}"

                logger.info(f"[Agent] 结果: {str(result)[:200]}")
                messages.append(ToolMessage(content=str(result), tool_call_id=tc.get("id", "")))

        # Max iterations exceeded — final answer
        for chunk in self._model.stream(messages):
            if chunk.content:
                yield chunk.content


if __name__ == "__main__":
    agent = ReactAgent()
    print("=== 流式测试 ===")
    for chunk in agent.execute_stream("扫地机器人如何日常保养？"):
        print(chunk, end="", flush=True)
