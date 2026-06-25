"""FastAPI 应用入口 —— 统一组装中间件、路由、异常处理器。"""
import os
import uuid
import time
import logging

from dotenv import load_dotenv
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.conversation import router as conversation_router
from app.api.routes.export import router as export_router
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.security import RateLimitMiddleware, SecurityHeadersMiddleware
from app.db.session import init_db

# ── 应用实例 ─────────────────────────────────────────────────────────
app = FastAPI(
    title="ApplianceRAG 智能客服 Backend",
    description="基于 ReAct Agent + RAG 的企业级智能客服后端服务",
    version="1.0.0",
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 安全头 ───────────────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)

# ── 限流（可配置开关）────────────────────────────────────────────────
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )

# ── 请求日志中间件 ──────────────────────────────────────────────────
logger = logging.getLogger("api")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000

    logger.info(
        "[%s] %s %s → %s  %.0fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ── 全局异常处理器 ──────────────────────────────────────────────────
@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("未捕获异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": 50000,
            "message": "服务器内部错误",
            "data": None,
        },
    )


@app.exception_handler(404)
async def not_found_handler(_: Request, __):
    return JSONResponse(
        status_code=404,
        content={
            "code": 40400,
            "message": "接口不存在",
            "data": None,
        },
    )


# ── 注册路由 ─────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(files_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(export_router)


@app.get("/")
def read_root():
    return {"code": 20000, "message": "ApplianceRAG 智能客服后端服务运行中", "data": None}


# 启动时初始化数据库表
init_db()


@app.on_event("startup")
def startup_load_knowledge():
    from app.rag.vector_store import VectorStoreService
    from app.utils.logger_handler import logger
    logger.info("[Startup] 开始加载知识库文件...")
    try:
        VectorStoreService().load_document()
        logger.info("[Startup] 知识库加载完成")
    except Exception as e:
        logger.error("[Startup] 知识库加载失败: %s", e)