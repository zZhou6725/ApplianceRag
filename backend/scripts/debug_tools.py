"""Agent 工具调试脚本 —— 单独测试每个工具、交互 REPL、API 连通性检查。"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.react_agent import ALL_TOOLS, TOOL_BY_NAME
from app.rag.vector_store import VectorStoreService
from app.rag.rag_service import RagSummarizeService
from app.core.config import settings


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def list_tools():
    print_header("可用工具列表")
    for i, tool in enumerate(ALL_TOOLS, 1):
        desc = tool.description or "(无描述)"
        print(f"  [{i}] {tool.name}")
        print(f"      {desc[:80]}")
    print(f"\n  共 {len(ALL_TOOLS)} 个工具")


def run_tool(tool_name: str, args: dict):
    tool = TOOL_BY_NAME.get(tool_name)
    if tool is None:
        print(f"未知工具: {tool_name}")
        print(f"可用工具: {', '.join(TOOL_BY_NAME.keys())}")
        return

    print_header(f"工具测试: {tool_name}")
    print(f"  参数: {json.dumps(args, ensure_ascii=False)}")

    start = time.perf_counter()
    try:
        result = tool.invoke(args)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  耗时: {elapsed:.1f}ms")
        print(f"  结果:\n{result}")
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  耗时: {elapsed:.1f}ms")
        print(f"  错误: {e}")

    # For RAG tool, also show raw retrieval
    if tool_name == "rag_summarize" and "query" in args:
        print(f"\n  -- 原始检索结果 (Top {settings.chroma_k}) --")
        try:
            vs = VectorStoreService()
            retriever = vs.get_retriever()
            docs = retriever.invoke(args["query"])[:settings.chroma_k]
            for i, doc in enumerate(docs, 1):
                source = doc.metadata.get("source", "?")
                snippet = doc.page_content[:150].replace("\n", " ")
                print(f"  [{i}] {source}")
                print(f"      {snippet}...")
        except Exception as e:
            print(f"  检索失败: {e}")


def run_interactive():
    print_header("Agent 工具交互调试")
    print("  输入工具名调用，格式: tool_name key=value ...")
    print("  可用命令: /list, /help, /quit")
    print(f"  可用工具: {', '.join(TOOL_BY_NAME.keys())}\n")

    while True:
        try:
            line = input("[debug] tool> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line in ("/quit", "/exit", "/q"):
            print("  已退出")
            break
        if line == "/list":
            list_tools()
            continue
        if line == "/help":
            print("  用法: <工具名> <key>=<value> ...")
            print("  示例: rag_summarize query=如何清洗滤网")
            print("  示例: get_weather city=深圳")
            print("  命令: /list /help /quit")
            continue

        parts = line.split(maxsplit=1)
        tool_name = parts[0]
        kwargs = {}
        if len(parts) > 1:
            for pair in parts[1].split():
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    kwargs[k] = v
        run_tool(tool_name, kwargs)


def check_connectivity():
    """检查外部 API 连通性。"""
    print_header("API 连通性检查")

    # Check DashScope (via embedding model)
    print("  DashScope Embedding API...", end=" ")
    try:
        from app.model.factory import embed_model
        _ = embed_model.embed_query("test")
        print("[OK] 正常")
    except Exception as e:
        print(f"[FAIL] 失败: {e}")

    # Check Amap
    print("  高德地图 API...", end=" ")
    try:
        import httpx
        key = settings.AMAP_API_KEY
        if not key:
            print("[FAIL] 未配置 AMAP_API_KEY")
        else:
            resp = httpx.get("https://restapi.amap.com/v3/ip", params={"key": key}, timeout=10)
            if resp.status_code == 200 and resp.json().get("status") == "1":
                city = resp.json().get("city", "未知")
                print(f"[OK] 正常 (IP 定位: {city})")
            else:
                print(f"[FAIL] 返回异常: {resp.json().get('info', resp.text[:80])}")
    except Exception as e:
        print(f"[FAIL] 失败: {e}")

    # Check ChromaDB
    print("  ChromaDB 向量库...", end=" ")
    try:
        vs = VectorStoreService()
        count = vs.vector_store._collection.count()
        print(f"[OK] 正常 (文档数: {count})")
    except Exception as e:
        print(f"[FAIL] 失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="Agent 工具调试器")
    parser.add_argument("--list", action="store_true", help="列出所有工具")
    parser.add_argument("--tool", type=str, help="指定要测试的工具名")
    parser.add_argument("--query", type=str, help="query 参数 (用于 rag_summarize)")
    parser.add_argument("--city", type=str, help="city 参数 (用于 get_weather)")
    parser.add_argument("--user-id", type=str, help="user_id 参数 (用于 fetch_external_data)")
    parser.add_argument("--month", type=str, help="month 参数 (用于 fetch_external_data)")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互调试模式")
    parser.add_argument("--check", action="store_true", help="检查 API 连通性")

    args = parser.parse_args()

    if args.list:
        list_tools()
        return

    if args.check:
        check_connectivity()
        return

    if args.interactive:
        run_interactive()
        return

    if args.tool:
        tool_args = {}
        if args.query:
            tool_args["query"] = args.query
        if args.city:
            tool_args["city"] = args.city
        if args.user_id:
            tool_args["user_id"] = args.user_id
        if args.month:
            tool_args["month"] = args.month
        run_tool(args.tool, tool_args)
        return

    # Default: show usage
    list_tools()
    print("\n  用法: python scripts/debug_tools.py [--list | --tool <name> ... | --interactive | --check]")
    print("  详情: python scripts/debug_tools.py --help")


if __name__ == "__main__":
    main()
