"""Cache abstraction layer — pluggable backends (memory / redis).

Replaces the in-memory LLMCache with a swappable backend while keeping
the same `get(query, prefix)` / `set(query, value, prefix)` interface.
"""

import hashlib
import time
from abc import ABC, abstractmethod

from app.core.config import settings
from app.utils.logger_handler import logger


class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None: ...

    @abstractmethod
    def set(self, key: str, value: str, ttl: int = 3600) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @property
    @abstractmethod
    def stats(self) -> dict: ...


class MemoryCache(CacheBackend):
    """In-process dict cache with TTL — same behaviour as the original LLMCache."""

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._hits = 0
        self._misses = 0
        self._hit_times: list[float] = []
        self._miss_times: list[float] = []
        self._recent_events: list[dict] = []

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry and time.time() - entry["ts"] < entry.get("ttl", 3600):
            self._hits += 1
            return entry["value"]
        if entry:
            del self._store[key]
        self._misses += 1
        return None

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        self._store[key] = {"value": value, "ts": time.time(), "ttl": ttl}

    def clear(self) -> None:
        self._store.clear()
        self._hits = 0
        self._misses = 0
        self._hit_times.clear()
        self._miss_times.clear()
        self._recent_events.clear()

    def record(self, hit: bool, elapsed_ms: float, query: str, prefix: str = ""):
        if hit:
            self._hit_times.append(elapsed_ms)
        else:
            self._miss_times.append(elapsed_ms)
        self._recent_events.append({
            "ts": time.strftime("%H:%M:%S"),
            "hit": hit,
            "elapsed_ms": round(elapsed_ms, 1),
            "query": query[:80],
            "prefix": prefix,
        })
        if len(self._recent_events) > 50:
            self._recent_events = self._recent_events[-50:]

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        avg_hit = round(sum(self._hit_times) / len(self._hit_times), 1) if self._hit_times else 0
        avg_miss = round(sum(self._miss_times) / len(self._miss_times), 1) if self._miss_times else 0
        return {
            "backend": "memory",
            "entries": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": round(self._hits / total, 4) if total else 0.0,
            "avg_hit_ms": avg_hit,
            "avg_miss_ms": avg_miss,
            "recent_events": self._recent_events[-20:],
        }


class RedisCache(CacheBackend):
    """Redis-backed cache. Falls back to MemoryCache if redis is unavailable."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: str | None = None):
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._client = None
        self._fallback = MemoryCache()
        self._connected = False
        self._try_connect()

    def _try_connect(self) -> None:
        try:
            import redis
            self._client = redis.Redis(
                host=self._host, port=self._port, db=self._db,
                password=self._password, socket_connect_timeout=2,
                decode_responses=True,
            )
            self._client.ping()
            self._connected = True
            logger.info("[CacheManager] Redis 连接成功")
        except Exception as e:
            logger.warning(f"[CacheManager] Redis 不可用 ({e})，降级到内存缓存")
            self._connected = False

    def _namespace(self, key: str) -> str:
        return f"zst:cache:{key}"

    def get(self, key: str) -> str | None:
        if self._connected and self._client:
            try:
                return self._client.get(self._namespace(key))
            except Exception as e:
                logger.warning(f"[CacheManager] Redis GET 失败: {e}")
        return self._fallback.get(key)

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        if self._connected and self._client:
            try:
                self._client.setex(self._namespace(key), ttl, value)
                return
            except Exception as e:
                logger.warning(f"[CacheManager] Redis SET 失败: {e}")
        self._fallback.set(key, value, ttl)

    def clear(self) -> None:
        if self._connected and self._client:
            try:
                self._client.delete(*self._client.keys(self._namespace("*")))
            except Exception as e:
                logger.warning(f"[CacheManager] Redis CLEAR 失败: {e}")
        self._fallback.clear()

    @property
    def stats(self) -> dict:
        base = {"backend": "redis" if self._connected else "memory(fallback)"}
        if self._connected:
            base["redis_host"] = f"{self._host}:{self._port}"
        base.update(self._fallback.stats)
        return base


class CacheManager:
    """Unified cache interface. Defaults to MemoryCache; set backend="redis" for Redis."""

    def __init__(self, backend: str = "memory", **kwargs):
        if backend == "redis":
            self._backend: CacheBackend = RedisCache(**kwargs)
        else:
            self._backend = MemoryCache()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(query: str, prefix: str = "") -> str:
        raw = f"{prefix}:{query}:{settings.LLM_MODEL}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, query: str, prefix: str = "") -> str | None:
        key = self._make_key(query, prefix)
        result = self._backend.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def set(self, query: str, value: str, prefix: str = "", ttl: int = 3600) -> None:
        key = self._make_key(query, prefix)
        self._backend.set(key, value, ttl)

    def record(self, hit: bool, elapsed_ms: float, query: str, prefix: str = ""):
        self._backend.record(hit, elapsed_ms, query, prefix)

    def clear(self) -> None:
        self._backend.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            **self._backend.stats,
            "manager_hits": self._hits,
            "manager_misses": self._misses,
            "manager_hit_rate": round(self._hits / total, 4) if total else 0.0,
        }


def _create_cache_manager() -> CacheManager:
    """根据环境变量创建缓存管理器。"""
    import os
    backend = os.getenv("CACHE_BACKEND", "memory")
    if backend == "redis":
        return CacheManager(
            backend="redis",
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD") or None,
        )
    return CacheManager(backend="memory")


cache_manager = _create_cache_manager()
