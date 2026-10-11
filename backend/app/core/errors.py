import logging
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("merchbrain.errors")


def _err(status, code, message, details=None):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})


def install(app):
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(request: Request, exc):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict", 429: "rate_limited"}.get(exc.status_code, "error")
        return _err(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def val_exc(request: Request, exc: RequestValidationError):
        det = [{"field": ".".join(str(x) for x in e["loc"][1:]), "problem": e["msg"]} for e in exc.errors()]
        return _err(422, "invalid_request", "Some inputs are not valid. Please check them and try again.", det)

    @app.exception_handler(Exception)
    async def any_exc(request: Request, exc: Exception):
        log.exception("unhandled error on %s %s", request.method, request.url.path)   # stack trace stays in the server log
        return _err(500, "internal_error", "Something went wrong on our side. The incident was logged; please try again.")
