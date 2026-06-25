"""RAG 缓存性能专项 benchmark — 测量三层缓存的延迟与吞吐。

用法: python scripts/bench_rag.py
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.rag_service import RagSummarizeService
from app.rag.vector_store import VectorStoreService
from harness.cache_manager import cache_manager
from harness.semantic_cache import semantic_cache


QUERIES = [
    "空调怎么省电",
    "扫地机器人滤网多久换",
    "冰箱不制冷怎么办",
    "洗衣机如何清洗内筒",
    "洗碗机不排水怎么修",
    "烤箱预热要多久",
    "微波炉加热不均匀",
    "空调滤网怎么清洗",
]


def clear_all_caches():
    cache_manager.clear()
    semantic_cache.clear()


def bench_single(query: str) -> dict:
    t0 = time.perf_counter()
    result = rag.rag_summarize(query)
    elapsed = (time.perf_counter() - t0) * 1000
    return {"query": query, "elapsed_ms": round(elapsed, 1), "result_len": len(result)}


def bench_concurrent(queries: list[str], workers: int = 4) -> dict:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda q: rag.rag_summarize(q), queries))
    elapsed = (time.perf_counter() - t0) * 1000
    qps = len(queries) / (elapsed / 1000)
    return {
        "total_ms": round(elapsed, 1),
        "num_queries": len(queries),
        "qps": round(qps, 1),
        "avg_ms": round(elapsed / len(queries), 1),
    }


if __name__ == "__main__":
    vs = VectorStoreService()
    rag = RagSummarizeService(vs)

    print("=" * 60)
    print("  RAG 缓存性能 Benchmark")
    print("=" * 60)

    # ── 冷缓存：首次查询 ──
    clear_all_caches()
    print("\n[1] 冷缓存 (完整 RAG + 向量检索 + LLM)")
    cold_results = [bench_single(q) for q in QUERIES[:4]]
    for r in cold_results:
        print(f"    {r['elapsed_ms']:>8.0f}ms  {r['query']}")
    cold_avg = sum(r["elapsed_ms"] for r in cold_results) / len(cold_results)
    print(f"    平均: {cold_avg:.0f}ms")

    # ── 精确缓存命中：同样的查询再问一次 ──
    print("\n[2] L2 精确缓存命中 (SHA256 完全匹配)")
    exact_results = [bench_single(q) for q in QUERIES[:4]]
    for r in exact_results:
        print(f"    {r['elapsed_ms']:>8.0f}ms  {r['query']}")
    exact_avg = sum(r["elapsed_ms"] for r in exact_results) / len(exact_results)
    improvement = (cold_avg - exact_avg) / cold_avg * 100
    print(f"    平均: {exact_avg:.0f}ms  (优化 {improvement:.1f}%)")

    # ── 语义缓存命中：相似但不同的查询 ──
    print("\n[3] L1 语义缓存命中 (embedding 相似度匹配)")
    similar_queries = [
        "空调怎样节电",
        "扫地机器人滤网更换周期",
        "冰箱冷气不足怎么办",
        "洗衣机内筒清洁方法",
    ]
    sem_results = [bench_single(q) for q in similar_queries]
    for r in sem_results:
        print(f"    {r['elapsed_ms']:>8.0f}ms  {r['query']}")
    sem_avg = sum(r["elapsed_ms"] for r in sem_results) / len(sem_results)
    improvement = (cold_avg - sem_avg) / cold_avg * 100
    print(f"    平均: {sem_avg:.0f}ms  (优化 {improvement:.1f}%)")

    # ── 并发吞吐 ──
    print("\n[4] 并发吞吐 (4 并发 × 语义缓存暖场)")
    conc = bench_concurrent(QUERIES, workers=4)
    print(f"    {conc['num_queries']} 请求 / {conc['total_ms']:.0f}ms")
    print(f"    QPS: {conc['qps']:.1f}")
    print(f"    平均延迟: {conc['avg_ms']:.0f}ms")

    # ── 缓存统计 ──
    print("\n[5] 缓存统计")
    stats = cache_manager.stats
    sem_stats = semantic_cache.stats
    print(f"    精确缓存: hits={stats['hits']} misses={stats['misses']} rate={stats['hit_rate']}")
    print(f"    语义答案: hits={sem_stats['semantic_answer_hits']} misses={sem_stats['semantic_answer_misses']} rate={sem_stats['semantic_answer_rate']}")
    print(f"    文档缓存: hits={sem_stats['doc_cache_hits']}")

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print("  汇总")
    print("=" * 60)
    print(f"  冷缓存延迟:   {cold_avg:.0f}ms")
    print(f"  精确缓存命中: {exact_avg:.0f}ms (优化 {int((cold_avg - exact_avg) / cold_avg * 100)}%)")
    print(f"  语义缓存命中: {sem_avg:.0f}ms (优化 {int((cold_avg - sem_avg) / cold_avg * 100)}%)")
    print(f"  峰值 QPS:     {conc['qps']:.1f}")

    # RAG 准确率（关键词匹配）
    print("\n[6] RAG 检索准确率（关键词匹配）")
    from app.rag.evaluation import RAGEvaluator

    cases_path = Path(__file__).resolve().parent / "rag_test_cases.json"
    if cases_path.exists():
        with open(cases_path, "r", encoding="utf-8") as f:
            cases = json.load(f)
        evaluator = RAGEvaluator(vs)
        result = evaluator.evaluate(cases, k=3)
        print(f"    测试用例: {len(cases)}")
        if result.get("chunk_hit_rate") is not None:
            print(f"    Chunk Hit@3:  {result['chunk_hit_rate']:.1%}")
        if result.get("precision_at_k") is not None:
            print(f"    Precision@3:  {result['precision_at_k']:.1%}")
        if result.get("doc_hit_rate") is not None:
            print(f"    Doc Hit@3:    {result['doc_hit_rate']:.1%}")
        if result.get("recall_at_k") is not None:
            print(f"    Recall@3:     {result['recall_at_k']:.1%}")

        # LLM-as-Judge 评测
        print("\n[7] LLM-as-Judge 评测（语义相关性）")
        llm_result = evaluator.evaluate_llm_judge(cases, k=3)
        print(f"    LLM Precision: {llm_result['llm_precision']:.1%}  ({llm_result['yes_count']}/{llm_result['num_queries']})")
        for d in llm_result["details"]:
            tag = "YES" if d["relevant"] else "NO "
            print(f"    [{tag}] {d['elapsed_ms']:>6.0f}ms  {d['query']}")