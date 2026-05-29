"""鉴权接口 —— 登录、获取当前用户信息。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import (
    DEMO_USERS,
    _verify_password,
    create_access_token,
    get_current_user,
)
from app.core.response import success

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


@router.post("/login")
def login(body: LoginRequest):
    user = DEMO_USERS.get(body.username)
    if not user or not _verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(body.username)
    return success(data={
        "token": token,
        "username": body.username,
        "display_name": user["display_name"],
    })


@router.get("/me")
def get_me(username: str = Depends(get_current_user)):
    user = DEMO_USERS[username]
    return success(data={
        "username": username,
        "display_name": user["display_name"],
    })