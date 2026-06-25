"""导出 OpenAPI 3.0 规范文件，可直接导入 Apifox / Postman / Swagger UI。

用法：
    python scripts/export_openapi.py                    # 离线导出到 api-docs/openapi.json
    python scripts/export_openapi.py --host http://127.0.0.1:8001   # 指定生产环境地址

Apifox 导入步骤：
    1. 打开 Apifox → 项目设置 → 导入数据
    2. 选择 "OpenAPI 3.0 (Swagger)"
    3. 选择文件 backend/api-docs/openapi.json
    4. 导入后所有接口自动按 Tag 分组，请求体/响应体 Schema 自动生成
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "api-docs"


def generate_openapi() -> dict:
    """离线生成 OpenAPI 规范，不依赖运行中的服务。"""
    from app.api.main import app
    return app.openapi()


def enhance_for_apifox(spec: dict, host: str) -> dict:
    """为 Apifox 增强 OpenAPI 规范：添加 server、全局认证、描述。"""
    spec.setdefault("servers", []).insert(0, {
        "url": host.rstrip("/"),
        "description": "开发环境",
    })

    # 全局 BearerAuth 安全方案
    spec.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "调用 POST /auth/login 获取 Token，格式: Bearer {token}",
    }

    # 需要认证的接口路径 (前缀匹配)
    auth_prefixes = ["/chat", "/conversations", "/export", "/auth/me", "/files/upload",
                     "/health/metrics", "/health/rag-eval"]
    for path, methods in spec.get("paths", {}).items():
        needs_auth = any(path.startswith(p) for p in auth_prefixes)
        # /auth/login 和 /health 健康检查不需要认证
        if needs_auth and path not in ("/auth/login",):
            for method in methods:
                methods[method].setdefault("security", []).append({"BearerAuth": []})

    # 添加接口级别 description
    spec.setdefault("info", {})["x-apifox"] = {
        "name": "ApplianceRAG",
        "description": "智能家电客服后端 API — 基于 ReAct Agent + RAG",
    }

    return spec


def main():
    parser = argparse.ArgumentParser(description="导出 OpenAPI 规范文件")
    parser.add_argument("--host", default="http://127.0.0.1:8001", help="部署后的服务地址")
    parser.add_argument("--out", default=None, help="输出文件路径")
    args = parser.parse_args()

    print("[1/3] 离线生成 OpenAPI 规范...")
    spec = generate_openapi()
    print(f"      标题: {spec.get('info', {}).get('title', '')}")
    print(f"      接口数: {len(spec.get('paths', {}))}")

    print("[2/3] 增强 Apifox 兼容性...")
    spec = enhance_for_apifox(spec, args.host)

    out_path = Path(args.out) if args.out else OUTPUT_DIR / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[3/3] 写入 {out_path}")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    file_size = out_path.stat().st_size
    print(f"\n导出完成！文件大小: {file_size / 1024:.1f} KB")
    print(f"\n→ Apifox 导入: 项目设置 → 导入数据 → OpenAPI 3.0 → 选择 api-docs/openapi.json")
    print(f"→ 也可直接输入 URL: {args.host}/openapi.json (需要服务运行中)")


if __name__ == "__main__":
    main()
