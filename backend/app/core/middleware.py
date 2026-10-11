import logging, time, json, threading
from collections import defaultdict, deque
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import get_settings
from app.monitoring.metrics import observe_request

log = logging.getLogger("merchbrain.access")
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()

SECURE_HEADERS = {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
                  "Cache-Control": "no-store", "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
                  "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                  "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'"}


class Hardening(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t = time.time()
        ip = request.client.host if request.client else "?"
        limit = get_settings().rate_limit_per_minute
        if request.url.path.startswith("/api") and limit > 0:
            key = f"{ip}"
            with _lock:
                q = _hits[key]
                while q and q[0] < t - 60:
                    q.popleft()
                if len(q) >= limit:
                    return JSONResponse(status_code=429, content={"error": {"code": "rate_limited", "message": "Too many requests. Please wait a moment and retry.", "details": None}},
                                        headers={"Retry-After": "30"})
                q.append(t)
        resp = await call_next(request)
        if request.url.path.startswith("/api") and request.headers.get("accept-language", "").lower().startswith("ar") and resp.headers.get("content-type", "").startswith("application/json"):
            resp = await _arabic(resp)
        if request.url.path not in ("/docs", "/redoc", "/openapi.json"):
            for k, v in SECURE_HEADERS.items():
                resp.headers[k] = v
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        observe_request(request.method, path, resp.status_code, t)
        log.info(json.dumps({"event": "request", "method": request.method, "path": path, "status": resp.status_code, "ms": round((time.time() - t) * 1000, 1)}))
        return resp


async def _arabic(resp):
    """Arabic UI: translate the sentences in a JSON response. Any failure returns the original English response untouched."""
    body = b"".join([chunk async for chunk in resp.body_iterator])
    try:
        from app.core.i18n_ar import translate_payload
        body2 = json.dumps(translate_payload(json.loads(body)), ensure_ascii=False, default=str).encode("utf-8")
    except Exception:
        log.exception("arabic translation failed; returning English")
        body2 = body
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in ("content-length",)}
    return Response(content=body2, status_code=resp.status_code, headers=headers, media_type="application/json")
