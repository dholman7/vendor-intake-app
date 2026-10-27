"""Uniform error envelope: every error response is {"error": {"code", "message", ...}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra


def not_found(entity: str) -> AppError:
    return AppError(404, f"{entity}_not_found", f"{entity.capitalize()} not found")


def _envelope(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, **extra}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status, content=_envelope(exc.code, exc.message, **exc.extra)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {
                # Drop the "body"/"query" prefix so clients see the field name itself.
                "field": ".".join(str(p) for p in err["loc"][1:]) or str(err["loc"][0]),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_error", "Request validation failed", fields=fields),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSONResponse(status_code=exc.status_code, content=_envelope(code, str(exc.detail)))
