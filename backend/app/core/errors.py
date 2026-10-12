"""AppError → JSON {code, message_vi, detail} (docs/CODING-GUIDE.md §6.1)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.messages import message


class AppError(Exception):
    def __init__(self, status: int, code: str, detail: str = "", **fmt: str):
        super().__init__(code)
        self.status, self.code, self.detail = status, code, detail
        self.message_vi = message(code, **fmt)

    def payload(self) -> dict[str, str]:
        return {"code": self.code, "message_vi": self.message_vi, "detail": self.detail}

    @classmethod
    def not_found(cls, what: str, ident: str) -> AppError:
        return cls(404, "not_found", f"{what} {ident}", what=what)

    @classmethod
    def internal(cls, detail: str) -> AppError:
        return cls(500, "internal", detail)


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(exc.payload(), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        err = AppError(422, "invalid_input", str(exc.errors())[:2000])
        return JSONResponse(err.payload(), status_code=422)
