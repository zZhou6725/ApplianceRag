#!/usr/bin/env python
"""
ApplianceRAG Agent CLI — 工程化 Agent 命令行入口

用法:
    python cli.py "扫地机器人如何保养？"        # 单次查询（流式输出）
    python cli.py --interactive                 # 交互式对话模式
    python cli.py --eval                        # 评测模式
    python cli.py --eval --cases FILE.json      # 自定义评测用例
    python cli.py --cache redis "问题"           # 启用 Redis 缓存
    python cli.py --no-memory "问题"             # 禁用长期记忆
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure the backend directory is on sys.path for imports
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from graph.agent_graph import AgentGraph
from harness.cache_manager import cache_manager
from harness.context_builder import ConversationState
from harness.memory_manager import memory_manager
from app.utils.logger_handler import logger


BUILTIN_EVAL_CASES = [
    {"query": "扫地机器人如何日常保养？", "expect_keywords": ["保养", "清洁", "滚刷", "滤网"], "min_hits": 1},
    {"query": "滤网需要多久清洗一次？", "expect_keywords": ["滤网", "清洗", "保养"], "min_hits": 1},
    {"query": "机器人提示尘盒已满怎么办？", "expect_keywords": ["尘盒", "清理", "垃圾"], "min_hits": 1},
    {"query": "深圳今天天气怎么样？", "expect_keywords": ["深圳", "天气", "°C"], "min_hits": 2},
    {"query": "帮我查一下我的使用记录", "expect_keywords": ["用户", "使用记录", "清扫"], "min_hits": 1},
    {"query": "小户型适合哪种扫地机器人？", "expect_keywords": ["机器人", "小户型"], "min_hits": 1},
]


def print_banner(extra: dict | None = None):
    print("\n" + "=" * 60)
    print("  ApplianceRAG Agent — 工程化智能客服 CLI")
    print("  架构: CLI -> Harness -> LangGraph -> Skills -> Tools")
    if extra:
        for k, v in extra.items():
            print(f"  {k}: {v}")
    print("=" * 60 + "\n")


def print_stats():
    cache_stats = cache_manager.stats
    mem_count = memory_manager.count()
    print(f"\n[统计] 缓存: {cache_stats['backend']} | "
          f"命中率 {cache_stats.get('manager_hit_rate', 0)*100:.1f}% | "
          f"记忆数: {mem_count}")
    print(f"[统计] 缓存详情: {json.dumps(cache_stats, ensure_ascii=False)}\n")


def run_single_query(agent: AgentGraph, query: str, stream: bool = True, show_stats: bool = False):
    if stream:
        print(f"\n[问题] {query}\n")
        print("[回答] ", end="", flush=True)
        t0 = time.perf_counter()
        for token in agent.stream(query):
            print(token, end="", flush=True)
        elapsed = time.perf_counter() - t0
        print(f"\n\n[耗时 {elapsed:.2f}s]")
    else:
        t0 = time.perf_counter()
        state = agent.run(query)
        elapsed = time.perf_counter() - t0
        print(f"[回答] {state['final_answer']}")
        print(f"\n[耗时 {elapsed:.2f}s]")

    if show_stats:
        print_stats()


def run_interactive(agent: AgentGraph):
    conv = ConversationState()
    print_banner()
    print("交互模式已启动。输入问题开始对话，输入 /quit 退出，输入 /clear 清空对话。")
    print("命令: /stats 查看缓存/记忆统计, /memory 查看召回的记忆\n")

    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not query:
            continue
        if query.lower() in ("/quit", "/exit", "/q"):
            print("再见！")
            break
        if query.lower() in ("/clear", "/c"):
            conv.clear()
            memory_manager.clear()
            print("[系统] 对话历史和记忆已清空\n")
            continue
        if query.lower() == "/stats":
            print_stats()
            continue
        if query.lower() == "/memory":
            memories = memory_manager.recall("", k=10)
            if memories:
                print("[记忆列表]")
                for m in memories:
                    print(f"  [{m['timestamp'][:10]}] {m['summary']}")
            else:
                print("[记忆列表] (空)")
            print()
            continue

        conv.add_message("user", query)
        history = conv.get_history()[:-1]

        print("\nApplianceRAG: ", end="", flush=True)
        t0 = time.perf_counter()
        full = ""
        stream = agent.stream(query, history)
        for token in stream:
            full += token
            print(token, end="", flush=True)
        elapsed = time.perf_counter() - t0

        conv.add_message("assistant", full)
        print(f"\n\n[耗时 {elapsed:.2f}s]\n")


def run_eval(agent: AgentGraph, cases_path: str | None = None, show_stats: bool = False):
    if cases_path:
        with open(cases_path, "r", encoding="utf-8") as f:
            cases = json.load(f)
    else:
        cases = BUILTIN_EVAL_CASES

    print(f"\n{'=' * 60}")
    print(f"  评测模式 — 共 {len(cases)} 个用例")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0

    for i, case in enumerate(cases, 1):
        query = case["query"]
        expect_kw = case.get("expect_keywords", [])
        min_hits = case.get("min_hits", 1)

        print(f"[{i}/{len(cases)}] {query}")
        print(f"         期望关键词: {expect_kw} (至少命中 {min_hits})")

        t0 = time.perf_counter()
        try:
            state = agent.run(query)
            answer = state.get("final_answer", "")
        except Exception as e:
            logger.error(f"评测用例 {i} 执行失败: {e}")
            answer = ""
        elapsed = time.perf_counter() - t0

        hits = sum(1 for kw in expect_kw if kw in answer)

        if hits >= min_hits:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(f"         命中: {hits}/{len(expect_kw)} | 耗时: {elapsed:.2f}s | {status}")
        if status == "FAIL":
            print(f"         回答预览: {answer[:120]}...")
        print()

    print(f"{'=' * 60}")
    print(f"  结果: {passed} 通过, {failed} 失败, 通过率 {passed / len(cases) * 100:.1f}%")
    print(f"{'=' * 60}\n")

    if show_stats:
        print_stats()


def main():
    parser = argparse.ArgumentParser(
        description="ApplianceRAG Agent CLI — 工程化智能客服命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py "扫地机器人如何保养？"         # 单次查询
  python cli.py -i                              # 交互式模式
  python cli.py -e                              # 评测模式（内置用例）
  python cli.py -e --cases my_cases.json        # 自定义评测用例
  python cli.py --cache redis "问题"            # Redis 缓存模式
  python cli.py --no-memory "问题"              # 禁用长期记忆
        """,
    )
    parser.add_argument("query", nargs="?", help="用户问题（直接查询模式）")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互式对话模式")
    parser.add_argument("-e", "--eval", dest="eval_mode", action="store_true", help="评测模式")
    parser.add_argument("--cases", type=str, default=None, help="评测用例 JSON 文件路径")
    parser.add_argument("--no-stream", action="store_true", help="禁用流式输出")
    parser.add_argument("--cache", type=str, default="memory", choices=["memory", "redis"],
                        help="缓存后端: memory(默认) / redis")
    parser.add_argument("--no-memory", dest="no_memory", action="store_true",
                        help="禁用长期记忆模块")
    parser.add_argument("--redis-host", type=str, default="localhost", help="Redis 主机地址")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis 端口")
    parser.add_argument("--stats", action="store_true", help="查询结束后显示缓存/记忆统计")
    args = parser.parse_args()

    if args.interactive:
        mode = "interactive"
    elif args.eval_mode:
        mode = "eval"
    elif args.query:
        mode = "query"
    else:
        parser.print_help()
        return

    # Configure cache backend
    if args.cache == "redis":
        cache_manager._backend = None  # Will be recreated, but simpler: just init a new one
        from harness.cache_manager import RedisCache
        cache_manager._backend = RedisCache(host=args.redis_host, port=args.redis_port)

    # Configure memory
    enable_memory = not args.no_memory

    extra_info = {
        "Cache": args.cache,
        "Memory": "ON" if enable_memory else "OFF",
    }
    if mode in ("query", "interactive"):
        print_banner(extra_info)

    agent = AgentGraph(enable_memory=enable_memory)

    if mode == "query":
        run_single_query(agent, args.query, stream=not args.no_stream, show_stats=args.stats)
    elif mode == "interactive":
        run_interactive(agent)
    elif mode == "eval":
        run_eval(agent, args.cases, show_stats=args.stats)


if __name__ == "__main__":
    main()
