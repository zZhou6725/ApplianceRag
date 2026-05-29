"""RAG 检索质量评测脚本 —— 支持 chunk 级 + 文档级评测 + 交互模式。"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.evaluation import RAGEvaluator, llm_cache
from app.rag.vector_store import VectorStoreService

# 用例同时指定 chunk 级关键词 + 文档级期望文件名，两者独立计算
BUILTIN_CASES = [
    {
        "query": "小户型适合哪种扫地机器人",
        "relevant_keywords": ["超薄", "机身厚度"],
        "relevant_docs": {"robot_vacuum_guide.txt"},
    },
    {
        "query": "空调温度多少度最省电",
        "relevant_keywords": ["温度设定", "省电"],
        "relevant_docs": {"aircon_manual.txt"},
    },
    {
        "query": "婴儿辅食怎么做，用什么机器",
        "relevant_keywords": ["辅食", "胡萝卜"],
        "relevant_docs": {"food_processor_guide.txt"},
    },
    {
        "query": "家里的智能家具如何日常保养，电饭锅，空调",
        "relevant_keywords": ["实木家具", "避免阳光直射"],
        "relevant_docs": {"furniture_care.txt"},
    },
    {
        "query": "扫地机器人和智能家居系统如何联动",
        "relevant_keywords": ["离家模式", "扫地机器人"],
        "relevant_docs": {"smart_home_system.txt"},
    },
    {
        "query": "机器人滤网多久换一次，怎么清洗",
        "relevant_keywords": ["滤网", "清洗滤网"],
        "relevant_docs": {"robot_vacuum_guide.txt"},
    },
    {
        "query": "E01故障代码是什么意思",
        "relevant_keywords": ["E01", "滚刷缠绕"],
        "relevant_docs": {"robot_vacuum_guide.txt"},
    },
    {
        "query": "家庭机器人能和小孩互动吗",
        "relevant_keywords": ["端茶", "讲故事"],
        "relevant_docs": {"humanoid_robot_manual.txt"},
    },
]


def load_cases(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)
    if not isinstance(cases, list):
        raise ValueError("测试用例文件需为 JSON 数组")
    for case in cases:
        if "query" not in case:
            raise ValueError("每条测试用例必须包含 query 字段")
        case.setdefault("relevant_keywords", [])
        case.setdefault("relevant_docs", [])
    return cases


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run_batch(cases: list[dict], k: int):
    vs = VectorStoreService()
    evaluator = RAGEvaluator(vs)
    retriever = vs.get_retriever()

    # 源多样性
    diversity = evaluator.source_diversity()
    print_header("RAG 检索质量评测")
    print(f"  向量库 chunks: {diversity['total_chunks']}")
    print(f"  唯一文档源:    {diversity['unique_sources']}")
    for s in diversity["source_names"]:
        print(f"    - {s}")
    if diversity["unique_sources"] <= 1:
        print(f"  [!] 警告: 只有 {diversity['unique_sources']} 个文档源，文档级指标将无法区分相关/不相关文档")
    print(f"  测试用例数:    {len(cases)}")
    print(f"  K 值:          {k}")

    has_chunk_labels = any(c.get("relevant_keywords") for c in cases)
    has_doc_labels = any(c.get("relevant_docs") for c in cases)

    for i, case in enumerate(cases, 1):
        query = case["query"]
        keywords = case.get("relevant_keywords", [])
        relevant_docs = set(case.get("relevant_docs", []))

        retrieved = retriever.invoke(query)[:k]

        print(f"\n── [{i}/{len(cases)}] {query}")

        # chunk 级详细展示
        if keywords:
            print(f"    期望关键词: {keywords}")
        chunk_hit_count = 0
        for rank, doc in enumerate(retrieved, 1):
            src = os.path.basename(doc.metadata.get("source", "?"))
            matched_kw = [kw for kw in keywords if kw in doc.page_content] if keywords else []
            marker = " *" if matched_kw else "  "
            snippet = doc.page_content[:100].replace("\n", " ")
            print(f"    [{rank}] {src}{marker}")
            print(f"        {snippet}...")
            if matched_kw:
                print(f"        >>> 命中: {matched_kw}")
                chunk_hit_count += 1

        # 打印各指标
        if has_chunk_labels and keywords:
            prec = evaluator.precision_at_k(query, keywords, k)
            cmrr = evaluator.mrr_at_k_chunks(query, keywords, k)
            print(f"    chunk 级: Precision@{k}={prec:.3f}  MRR={cmrr:.3f}  (命中 {chunk_hit_count}/{len(retrieved)})")

        if has_doc_labels and relevant_docs:
            recall = evaluator.recall_at_k(query, relevant_docs, k)
            dhit = evaluator.hit_rate(query, relevant_docs, k)
            dmrr = evaluator.mrr(query, relevant_docs, k)
            retrieved_docs = {os.path.basename(doc.metadata.get("source", "")) for doc in retrieved}
            print(f"    文档级: Recall@{k}={recall:.3f}  Hit={dhit:.1f}  MRR={dmrr:.3f}  (检索到: {retrieved_docs})")

    # 汇总
    result = evaluator.evaluate(cases, k)
    print_header("汇总指标")

    if result["precision_at_k"] is not None:
        print(f"  [chunk 级] Precision@{k}: {result['precision_at_k']}")
        print(f"  [chunk 级] MRR@{k}:      {result['chunk_mrr']}")
        print(f"  [chunk 级] Hit Rate@{k}:  {result['chunk_hit_rate']}")
        print(f"  [chunk 级] 标注用例数:    {result['num_with_chunk_labels']}")

    if result["recall_at_k"] is not None:
        print(f"  [文档级] Recall@{k}:  {result['recall_at_k']}")
        print(f"  [文档级] Hit Rate@{k}: {result['doc_hit_rate']}")
        print(f"  [文档级] MRR@{k}:     {result['doc_mrr']}")
        print(f"  [文档级] 标注用例数:   {result['num_with_doc_labels']}")

    cache_stats = llm_cache.stats
    print(f"\n  LLM 缓存命中率: {cache_stats['hit_rate']} (hits={cache_stats['hits']} misses={cache_stats['misses']})")


def run_interactive(k: int):
    vs = VectorStoreService()
    retriever = vs.get_retriever()
    diversity = RAGEvaluator(vs).source_diversity()

    print_header("RAG 交互调试模式")
    print(f"  文档源 ({diversity['unique_sources']}): {', '.join(diversity['source_names'])}")
    print(f"  Chunks: {diversity['total_chunks']}, K = {k}")
    print("  输入查询查看检索结果，输入 /quit 退出\n")

    while True:
        try:
            line = input("[search] query> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line in ("/quit", "/exit", "/q"):
            print("  已退出")
            break

        # 支持 query | keyword1,keyword2 格式快速标注
        query = line
        extra_kw = []
        if "|" in line:
            query, kw_str = line.split("|", 1)
            extra_kw = [kw.strip() for kw in kw_str.split(",") if kw.strip()]
            query = query.strip()

        start = time.perf_counter()
        docs = retriever.invoke(query)[:k]
        elapsed = (time.perf_counter() - start) * 1000

        print(f"  耗时: {elapsed:.1f}ms, 返回 {len(docs)} 条结果:")
        for i, doc in enumerate(docs, 1):
            source = os.path.basename(doc.metadata.get("source", "?"))
            matched = [kw for kw in extra_kw if kw in doc.page_content] if extra_kw else []
            marker = " *HIT*" if matched else ""
            snippet = doc.page_content[:150].replace("\n", " ")
            print(f"    [{i}] {source}{marker}")
            print(f"        {snippet}...")
            if matched:
                print(f"        >>> 命中关键词: {matched}")
        if extra_kw:
            hits = sum(1 for doc in docs if any(kw in doc.page_content for kw in extra_kw))
            print(f"  关键词命中: {hits}/{len(docs)} chunks")
        print()


def main():
    parser = argparse.ArgumentParser(description="RAG 检索质量评测")
    parser.add_argument("--cases", type=str, help="JSON 测试用例文件路径")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互调试模式")
    parser.add_argument("--k", type=int, default=3, help="检索 Top-K 数量")
    args = parser.parse_args()

    if args.interactive:
        run_interactive(args.k)
        return

    cases = load_cases(args.cases) if args.cases else BUILTIN_CASES
    run_batch(cases, args.k)


if __name__ == "__main__":
    main()
