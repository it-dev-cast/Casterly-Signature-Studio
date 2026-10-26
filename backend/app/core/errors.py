"""Application errors and global exception handlers producing the standard error envelope."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("signature_studio")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def not_found(entity: str) -> AppError:
    return AppError(404, "NOT_FOUND", f"{entity} not found.")


def conflict(code: str, message: str) -> AppError:
    return AppError(409, code, message)


def bad_request(code: str, message: str) -> AppError:
    return AppError(400, code, message)


def _error(status: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    body: dict = {"success": False, "error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return _error(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            msg = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
            details.append({"field": ".".join(loc) or None, "message": msg})
        first = details[0] if details else {"field": None, "message": "Invalid request."}
        message = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
        return _error(422, "VALIDATION_ERROR", message, details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return _error(exc.status_code, _HTTP_CODES.get(exc.status_code, "HTTP_ERROR"), message)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        # Full details are logged server-side and never leaked to the client.
        logger.exception("Unhandled error", exc_info=exc)
        return _error(500, "INTERNAL_ERROR", "An unexpected error occurred. Please try again.")
