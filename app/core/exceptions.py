class AppError(Exception):
    """业务异常基类，由 main.py 中注册的处理器统一转换为 HTTP 响应。"""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AuthenticationError(AppError):
    status_code = 401


class ConflictError(AppError):
    status_code = 409


class ValidationError(AppError):
    status_code = 422
