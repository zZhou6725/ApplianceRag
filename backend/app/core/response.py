"""统一响应封装 —— 所有接口返回格式一致，前端可统一处理。"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=20000, description="业务状态码，20000 表示成功")
    message: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="响应数据")

    model_config = {"from_attributes": True}


def success(data: Any = None, message: str = "success") -> dict:
    """快捷成功响应（dict 格式，兼容 StreamingResponse 场景）。"""
    return {"code": 20000, "message": message, "data": data}


def fail(code: int = 50000, message: str = "服务器内部错误", data: Any = None) -> dict:
    """快捷失败响应。"""
    return {"code": code, "message": message, "data": data}


class PaginatedData(BaseModel):
    total: int = Field(..., ge=0)
    items: list[Any] = Field(default_factory=list)


class PaginatedResponse(ApiResponse[PaginatedData]):
    code: int = Field(default=20000)
    message: str = Field(default="success")
    data: PaginatedData | None = None