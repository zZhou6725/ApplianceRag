"""数据入库质量评测脚本 —— 检查文档加载、向量库健康、MD5 去重、自检索验证。"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.rag.vector_store import VectorStoreService
from app.utils.file_handler import (
    get_file_md5_hex,
    listdir_with_allowed_type,
    csv_loader,
    pdf_loader,
    txt_loader,
)
from app.utils.logger_handler import logger
from app.utils.path_tools import get_abs_path


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_files(data_dir: str, allowed_types: tuple) -> list[str]:
    """扫描 data/ 目录，返回文件列表。"""
    files = listdir_with_allowed_type(data_dir, allowed_types)
    print(f"  文件总数: {len(files)}")
    type_counts: dict[str, int] = {}
    for f in files:
        ext = os.path.splitext(f)[1]
        type_counts[ext] = type_counts.get(ext, 0) + 1
    for ext, count in sorted(type_counts.items()):
        print(f"    {ext}: {count} 个")
    return files


def load_file_documents(filepath: str):
    """加载单个文件为文档列表。"""
    if filepath.endswith(".txt"):
        return txt_loader(filepath)
    elif filepath.endswith(".pdf"):
        return pdf_loader(filepath)
    elif filepath.endswith(".csv"):
        return csv_loader(filepath)
    return []


def check_chunks(files: list[str]):
    """统计每个文件的 chunk 分布。"""
    vs = VectorStoreService()
    total_chunks = 0
    total_chars = 0

    print_header("文档切片统计")

    for fp in files:
        docs = load_file_documents(fp)
        if not docs:
            print(f"  {os.path.basename(fp)}: 无有效内容")
            continue
        split_docs = vs.splitter.split_documents(docs)
        n = len(split_docs)
        avg_len = sum(len(d.page_content) for d in split_docs) / n if n else 0
        total_chunks += n
        total_chars += sum(len(d.page_content) for d in split_docs)
        print(f"  {os.path.basename(fp)}: {len(docs)} page(s) -> {n} chunks, avg {avg_len:.0f} chars/chunk")

    if total_chunks:
        print(f"\n  总计: {total_chunks} chunks, avg {total_chars/total_chunks:.0f} chars/chunk")


def check_md5(files: list[str]):
    """验证 MD5 去重记录。"""
    md5_path = get_abs_path(settings.chroma_md5_store)
    print_header("MD5 去重检查")

    if not os.path.exists(md5_path):
        print(f"  MD5 记录文件不存在: {md5_path}")
        print(f"  提示: 运行 python scripts/ingest_knowledge.py 初始化")
        return

    with open(md5_path, "r", encoding="utf-8") as f:
        stored = {line.strip() for line in f if line.strip()}

    current = {}
    for fp in files:
        md5 = get_file_md5_hex(fp)
        if md5:
            current[fp] = md5

    missing = [fp for fp, md5 in current.items() if md5 not in stored]
    orphaned = stored - set(current.values())

    print(f"  文件数: {len(files)}")
    print(f"  已入库 (MD5 匹配): {len(files) - len(missing)}")
    print(f"  未入库 (MD5 缺失): {len(missing)}")
    if missing:
        for fp in missing:
            print(f"    - {os.path.basename(fp)}")
    if orphaned:
        print(f"  孤儿 MD5 记录: {len(orphaned)} (文件已删除但记录还在)")
    if not missing and not orphaned:
        print(f"  MD5 去重记录完整一致 [OK]")


def check_vector_store():
    """检查向量库健康状态。"""
    print_header("向量库健康检查")
    vs = VectorStoreService()
    store = vs.vector_store
    try:
        count = store._collection.count()
        print(f"  Collection: {settings.CHROMA_COLLECTION_NAME}")
        print(f"  文档总数:   {count}")
        if count == 0:
            print(f"  [!] 向量库为空，请先运行 python scripts/ingest_knowledge.py")
    except Exception as e:
        print(f"  [!] 无法获取向量库信息: {e}")


def check_self_retrieval(files: list[str], sample: int):
    """抽样自检索验证：从文档取一段话，检索回来看能否命中自身。"""
    print_header("自检索验证 (Self-Retrieval)")

    vs = VectorStoreService()
    retriever = vs.get_retriever()

    try:
        all_docs = vs.vector_store.get()
    except Exception:
        print("  [!] 向量库为空，跳过自检索验证")
        return

    # Build source filename -> first chunk content mapping
    source_chunks: dict[str, str] = {}
    for doc_id, metadata, content in zip(all_docs["ids"], all_docs["metadatas"], all_docs["documents"]):
        source = os.path.basename(metadata.get("source", ""))
        if source and source not in source_chunks:
            source_chunks[source] = content

    candidates = [(fname, content) for fname, content in source_chunks.items()]
    if not candidates:
        print("  [!] 无可用 chunk 进行自检索")
        return

    import random
    if sample > 0:
        candidates = random.sample(candidates, min(sample, len(candidates)))

    total = len(candidates)
    hits = 0
    for fname, chunk_text in candidates:
        query = chunk_text[:100]
        retrieved = retriever.invoke(query)[:5]
        retrieved_sources = [os.path.basename(doc.metadata.get("source", "")) for doc in retrieved]
        if fname in retrieved_sources:
            hits += 1
            rank = retrieved_sources.index(fname) + 1
            print(f"  [OK] {fname} -> rank {rank}")
        else:
            print(f"  [FAIL] {fname} -> 未命中 (检索到: {retrieved_sources[:3]})")

    rate = hits / total * 100 if total else 0
    print(f"\n  自检索命中率: {hits}/{total} = {rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="知识库入库质量评测")
    parser.add_argument("--sample", type=int, default=0,
                        help="自检索抽样数量 (0=全部)")
    args = parser.parse_args()

    data_dir = str(get_abs_path(settings.chroma_data_path))
    allowed_types = tuple(settings.chroma_allow_file_types)

    print_header("知识库入库质量评测")
    print(f"  数据目录: {data_dir}")
    print(f"  允许类型: {allowed_types}")

    files = check_files(data_dir, allowed_types)

    if not files:
        print("\n  [!] 数据目录为空，请先添加知识库文件")
        return

    check_chunks(files)
    check_md5(files)
    check_vector_store()
    check_self_retrieval(files, args.sample)

    print_header("评测完成")


if __name__ == "__main__":
    main()
