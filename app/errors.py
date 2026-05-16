from collections.abc import Sequence
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


STATUS_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    402: "PAYMENT_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_SERVER_ERROR",
    502: "UPSTREAM_ERROR",
}


def error_body(
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    details: Any = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code or STATUS_ERROR_CODES.get(status_code, "ERROR"),
            "message": message,
            "status": status_code,
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def _stringify_detail(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, Sequence) and not isinstance(detail, (bytes, bytearray, str)):
        return "请求参数不正确"
    return str(detail)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(status_code=exc.status_code, message=_stringify_detail(exc.detail)),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(
            status_code=422,
            code="VALIDATION_ERROR",
            message="请求参数不正确",
            details=jsonable_encoder(exc.errors()),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_body(status_code=500, message="服务器内部错误"),
    )
