from app.model.factory import chat_model
from app.utils.logger_handler import logger
from harness.cache_manager import cache_manager
from harness.context_builder import ContextBuilder
from harness.memory_manager import memory_manager
from harness.prompt_manager import PromptManager
from harness.result_validator import ResultValidator
from harness.tool_router import ToolRouter
from graph.state import AgentState


def recall_memory_node(state: AgentState) -> dict:
    """Retrieve relevant past conversation memories and inject into context."""
    query = state["query"]
    memories = memory_manager.recall(query, k=3)
    metadata = dict(state.get("metadata", {}))

    if memories:
        formatted = memory_manager.format_memories(memories)
        metadata["memory_context"] = formatted
        logger.info(f"[Graph] 记忆召回: {len(memories)} 条")
    else:
        metadata.pop("memory_context", None)

    return {"metadata": metadata}


def classify_intent_node(state: AgentState) -> dict:
    query = state["query"]
    # If memories exist, prepend them to the query for better intent classification
    enriched_query = query
    memory_ctx = state.get("metadata", {}).get("memory_context", "")
    if memory_ctx:
        enriched_query = f"{memory_ctx}\n当前问题: {query}"

    intent = ToolRouter.classify_intent(enriched_query)
    metadata = dict(state.get("metadata", {}))
    if intent == "report":
        metadata["report_mode"] = True
    logger.info(f"[Graph] 意图分类: {intent} (query: {query[:50]})")
    return {"intent": intent, "metadata": metadata}


def dispatch_skill_node(state: AgentState) -> dict:
    intent = state.get("intent", "consultation")
    skill = ToolRouter.route(intent)

    if skill is None:
        return {
            "skill_results": state.get("skill_results", []) + [{
                "skill_name": "unknown",
                "output": None,
                "error": f"未找到意图 {intent} 对应的技能",
            }],
        }

    context = ContextBuilder.build_context(state)
    # Check cache for RAG queries
    if intent == "consultation":
        cached = cache_manager.get(state["query"], prefix="rag")
        if cached:
            logger.info("[Graph] RAG 缓存命中")
            results = list(state.get("skill_results", []))
            results.append({"skill_name": "rag", "output": cached, "error": None, "from_cache": True})
            return {"skill_results": results}

    logger.info(f"[Graph] 调度技能: {skill.name} (意图: {intent})")

    result = skill.run(state["query"], context)
    entry = {
        "skill_name": result.skill_name,
        "output": result.output,
        "error": result.error,
        "elapsed_ms": result.elapsed_ms,
        "retries": result.retries,
    }

    # Cache successful RAG results
    if intent == "consultation" and not result.error and result.output:
        cache_manager.set(state["query"], str(result.output), prefix="rag")

    results = list(state.get("skill_results", []))
    results.append(entry)
    metadata = dict(state.get("metadata", {}))
    if isinstance(result.output, dict) and result.output.get("report_mode"):
        metadata["report_mode"] = True

    return {"skill_results": results, "metadata": metadata}


def assemble_result_node(state: AgentState) -> dict:
    results = state.get("skill_results", [])
    error_count = state.get("error_count", 0)

    if not results:
        return {"final_answer": ResultValidator.get_fallback_response()}

    latest = results[-1]
    if ResultValidator.validate(latest):
        logger.info("[Graph] 结果校验通过")
        return {"error_count": 0}

    error_count += 1
    logger.warning(f"[Graph] 结果校验失败 (第{error_count}次), skill={latest.get('skill_name')}")

    if not ResultValidator.should_retry(error_count):
        return {
            "final_answer": ResultValidator.get_fallback_response(),
            "error_count": error_count,
        }
    return {"error_count": error_count}


def generate_output_node(state: AgentState) -> dict:
    if state.get("final_answer"):
        return {"final_answer": state["final_answer"]}

    metadata = state.get("metadata", {})

    # Inject memory context into system prompt if available
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

    try:
        full = ""
        for chunk in chat_model.stream(messages):
            if chunk.content:
                full += chunk.content
        return {"final_answer": full}
    except Exception as e:
        logger.error(f"[Graph] LLM 生成失败: {e}")
        return {"final_answer": ResultValidator.get_fallback_response()}


def store_memory_node(state: AgentState) -> dict:
    """Store the completed conversation turn as a long-term memory."""
    answer = state.get("final_answer", "")
    query = state["query"]
    if answer and query:
        try:
            memory_manager.store(query, answer)
        except Exception as e:
            logger.warning(f"[Graph] 记忆存储失败: {e}")
    return {}
