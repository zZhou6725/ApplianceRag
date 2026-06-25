import json
import time
from pathlib import Path

import psutil
from fastapi import APIRouter

from app.core.response import success
from app.rag.evaluation import RAGEvaluator
from harness.cache_manager import cache_manager
from harness.semantic_cache import semantic_cache
from app.rag.vector_store import VectorStoreService

router = APIRouter(tags=["health"])

_start_time = time.time()

_EVAL_CASES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "rag_test_cases.json"


@router.get("/health", summary="健康检查", description="返回服务运行状态")
def health_check():
    return success(message="ok")


@router.get("/health/metrics", summary="服务指标", description="返回缓存命中率、CPU、内存等运行时指标")
def get_metrics():
    """返回缓存命中率 + 服务运行状态"""
    process = psutil.Process()
    mem = process.memory_info()
    uptime = time.time() - _start_time

    return success(data={
        "uptime_seconds": int(uptime),
        "memory_mb": round(mem.rss / 1024 / 1024, 1),
        "cpu_percent": process.cpu_percent(interval=0.1),
        "cache": {**cache_manager.stats, "semantic": semantic_cache.stats},
    })


@router.get("/health/rag-eval", summary="RAG 检索评测", description="运行 RAG 检索质量评测，返回 Precision/MRR/Recall 等指标")
def run_rag_eval(k: int = 3):
    """运行 RAG 检索质量评测并返回指标"""
    if not _EVAL_CASES_PATH.exists():
        return success(data={"error": f"测试用例文件不存在: {_EVAL_CASES_PATH}"})

    with open(_EVAL_CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    evaluator = RAGEvaluator(VectorStoreService())
    result = evaluator.evaluate(cases, k)
    result["num_cases"] = len(cases)
    result["cache"] = cache_manager.stats

    return success(data=result)
