"""端到端对话测试脚本 —— 测试完整 Agent 流式对话、延迟统计、关键词验证。"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.react_agent import ReactAgent

BUILTIN_CASES = [
    {
        "query": "扫地机器人如何日常保养？",
        "expect_keywords": ["保养", "滤网", "清洁"],
        "min_keywords": 1,
    },
    {
        "query": "滤网多久换一次？",
        "expect_keywords": ["滤网", "更换", "月"],
        "min_keywords": 1,
    },
    {
        "query": "今天天气怎么样",
        "expect_keywords": [],
        "min_keywords": 0,
    },
]


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def load_cases(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)
    if not isinstance(cases, list):
        raise ValueError("测试用例文件需为 JSON 数组")
    for case in cases:
        if "query" not in case:
            raise ValueError("每条测试用例必须包含 query 字段")
        case.setdefault("expect_keywords", [])
        case.setdefault("min_keywords", 0)
    return cases


def run_single_query(agent: ReactAgent, query: str, expect_keywords: list[str], min_keywords: int) -> dict:
    """运行单条查询，返回测试结果。"""
    print(f"  查询: {query}")
    print(f"  预期关键词: {expect_keywords} (至少命中 {min_keywords} 个)")

    accumulated = ""
    first_token_ts = None
    start_ts = time.perf_counter()

    try:
        for chunk in agent.execute_stream(query):
            if first_token_ts is None and chunk:
                first_token_ts = time.perf_counter()
            accumulated += chunk
    except Exception as e:
        elapsed = time.perf_counter() - start_ts
        print(f"  [FAIL] 异常: {e}")
        return {"query": query, "passed": False, "error": str(e),
                "ttft_ms": 0, "total_ms": elapsed * 1000,
                "response_len": len(accumulated), "response_preview": accumulated[:200]}

    end_ts = time.perf_counter()
    ttft_ms = (first_token_ts - start_ts) * 1000 if first_token_ts else 0
    total_ms = (end_ts - start_ts) * 1000

    # Keyword check
    hits = [kw for kw in expect_keywords if kw in accumulated]
    passed = len(hits) >= min_keywords

    status = "[OK] PASS" if passed else "[FAIL] FAIL"
    print(f"  {status} | TTFT: {ttft_ms:.0f}ms | 总耗时: {total_ms:.0f}ms | 响应长度: {len(accumulated)} 字")
    print(f"  命中关键词: {hits} (需要 ≥{min_keywords})")
    if accumulated:
        preview = accumulated[:200].replace("\n", " ")
        print(f"  响应预览: {preview}...")
    print()

    return {
        "query": query,
        "passed": passed,
        "ttft_ms": round(ttft_ms, 1),
        "total_ms": round(total_ms, 1),
        "response_len": len(accumulated),
        "hits": hits,
        "expected": expect_keywords,
        "response_preview": accumulated[:300],
    }


def run_batch(cases: list[dict]):
    agent = ReactAgent()
    results = []
    passed = 0
    failed = 0

    print_header(f"端到端对话测试 ({len(cases)} 条用例)")

    for i, case in enumerate(cases, 1):
        print(f"── [{i}/{len(cases)}] ──")
        result = run_single_query(
            agent,
            case["query"],
            case.get("expect_keywords", []),
            case.get("min_keywords", 0),
        )
        results.append(result)
        if result["passed"]:
            passed += 1
        else:
            failed += 1

    # Summary
    print_header("测试汇总")
    print(f"  总计: {len(results)} | PASS: {passed} | FAIL: {failed}")
    if results:
        ttfts = [r["ttft_ms"] for r in results if r["ttft_ms"] > 0]
        totals = [r["total_ms"] for r in results]
        if ttfts:
            print(f"  首Token延迟: min={min(ttfts):.0f}ms max={max(ttfts):.0f}ms avg={sum(ttfts)/len(ttfts):.0f}ms")
        if totals:
            print(f"  总耗时:      min={min(totals):.0f}ms max={max(totals):.0f}ms avg={sum(totals)/len(totals):.0f}ms")

    # Show failures
    if failed:
        print(f"\n  失败用例:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['query']}")
                print(f"    命中: {r.get('hits', [])} / 期望: {r.get('expected', [])}")


def main():
    parser = argparse.ArgumentParser(description="端到端对话测试")
    parser.add_argument("--cases", type=str, help="JSON 测试用例文件路径")
    parser.add_argument("--query", type=str, help="单条查询测试")
    args = parser.parse_args()

    if args.query:
        agent = ReactAgent()
        print_header("单条查询测试")
        run_single_query(agent, args.query, [], 0)
        return

    cases = load_cases(args.cases) if args.cases else BUILTIN_CASES
    run_batch(cases)


if __name__ == "__main__":
    main()
