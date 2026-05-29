"""JWT 鉴权模块 —— 令牌生成、验证、FastAPI 依赖注入。"""
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(plain: str, hashed: str) -> bool:
    return _hash_password(plain) == hashed


# 演示用户（生产环境替换为数据库 + bcrypt）
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": _hash_password("admin123"),
        "display_name": "管理员",
    },
}


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """FastAPI 依赖：从 Authorization header 解析当前用户名。"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    if username not in DEMO_USERS:
        raise HTTPException(status_code=401, detail="用户不存在")
    return username