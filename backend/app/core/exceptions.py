"""全局自定义异常 —— 统一错误码与 HTTP 状态映射。"""
from typing import Any


class AppException(Exception):
    """业务异常基类，所有自定义异常继承此类。"""

    def __init__(
        self,
        message: str = "服务器内部错误",
        code: int = 50000,
        status_code: int = 500,
        detail: Any = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "资源不存在", detail: Any = None):
        super().__init__(message=message, code=40400, status_code=404, detail=detail)


class BadRequestError(AppException):
    def __init__(self, message: str = "请求参数有误", detail: Any = None):
        super().__init__(message=message, code=40000, status_code=400, detail=detail)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "未登录或令牌失效", detail: Any = None):
        super().__init__(message=message, code=40100, status_code=401, detail=detail)


class ForbiddenError(AppException):
    def __init__(self, message: str = "无权限访问", detail: Any = None):
        super().__init__(message=message, code=40300, status_code=403, detail=detail)


class LLMServiceError(AppException):
    def __init__(self, message: str = "LLM 服务调用失败", detail: Any = None):
        super().__init__(message=message, code=50200, status_code=502, detail=detail)


class VectorStoreError(AppException):
    def __init__(self, message: str = "向量库服务异常", detail: Any = None):
        super().__init__(message=message, code=50201, status_code=502, detail=detail)


class RateLimitError(AppException):
    def __init__(self, message: str = "请求过于频繁，请稍后再试"):
        super().__init__(message=message, code=42900, status_code=429)