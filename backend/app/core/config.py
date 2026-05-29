"""统一配置管理 —— 所有配置集中在此，通过环境变量与 pydantic-settings 加载。"""
from pathlib import Path
from functools import lru_cache

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def _load_yaml(filename: str) -> dict:
    path = BACKEND_DIR / "config" / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ── DashScope / LLM ──────────────────────────────────────────────
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "qwen3-max"
    EMBEDDING_MODEL: str = "text-embedding-v4"

    # ── 数据库 ───────────────────────────────────────────────────────
    DATABASE_URL: str = ""
    AMAP_API_KEY: str = ""

    # ── ChromaDB 向量库 ─────────────────────────────────────────────
    CHROMA_DB_DIR: str = "chroma_db"
    CHROMA_COLLECTION_NAME: str = "agent"
    ANONYMIZED_TELEMETRY: bool = False

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── 日志 ─────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── 限流 ─────────────────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── JWT ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # ── RAG 参数（来自 config/rag.yml 的覆盖或默认值）──────────────
    @property
    def rag_chat_model(self) -> str:
        rag_yml = _load_yaml("rag.yml")
        return rag_yml.get("chat_model_name", self.LLM_MODEL)

    @property
    def rag_embedding_model(self) -> str:
        rag_yml = _load_yaml("rag.yml")
        return rag_yml.get("embedding_model_name", self.EMBEDDING_MODEL)

    # ── Chroma 参数（来自 YAML 或默认值）────────────────────────────
    @property
    def chroma_persist_dir(self) -> str:
        yml = _load_yaml("chroma.yml")
        return yml.get("persist_directory", self.CHROMA_DB_DIR)

    @property
    def chroma_k(self) -> int:
        return _load_yaml("chroma.yml").get("k", 3)

    @property
    def chroma_chunk_size(self) -> int:
        return _load_yaml("chroma.yml").get("chunk_size", 200)

    @property
    def chroma_chunk_overlap(self) -> int:
        return _load_yaml("chroma.yml").get("chunk_overlap", 20)

    @property
    def chroma_separators(self) -> list[str]:
        return _load_yaml("chroma.yml").get(
            "separators",
            ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""],
        )

    @property
    def chroma_data_path(self) -> str:
        return _load_yaml("chroma.yml").get("data_path", "data")

    @property
    def chroma_allow_file_types(self) -> list[str]:
        return _load_yaml("chroma.yml").get("allow_knowledge_file_type", ["txt", "pdf", "csv"])

    @property
    def chroma_md5_store(self) -> str:
        return _load_yaml("chroma.yml").get("md5_hex_store", "md5.text")

    # ── Prompt 文件路径（来自 YAML）────────────────────────────────
    @property
    def main_prompt_path(self) -> str:
        return _load_yaml("prompts.yml").get("main_prompt_path", "prompts/main_prompt.txt")

    @property
    def report_prompt_path(self) -> str:
        return _load_yaml("prompts.yml").get("report_prompt_path", "prompts/report_prompt.txt")

    @property
    def rag_summarize_prompt_path(self) -> str:
        return _load_yaml("prompts.yml").get("rag_summarize_prompt_path", "prompts/rag_summarize.txt")

    # ── Agent 相关（来自 YAML）──────────────────────────────────────
    @property
    def external_data_path(self) -> str:
        return _load_yaml("agent.yml").get("external_data_path", "data/external/records.csv")

    @property
    def db_path(self) -> Path:
        db_dir = BACKEND_DIR / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "app.db"

    @property
    def chroma_dir(self) -> Path:
        p = Path(self.CHROMA_DB_DIR)
        return p if p.is_absolute() else BACKEND_DIR / p

    @property
    def logs_dir(self) -> Path:
        p = BACKEND_DIR / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()