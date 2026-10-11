"""Redis cache with transparent in-process fallback (used in tests / single-node dev)."""
import json, time, threading
from app.core.config import get_settings

_local: dict[str, tuple[float, str]] = {}
_lock = threading.Lock()
_redis = None
PREFIX = "smb:"


def _r():
    global _redis
    url = get_settings().redis_url
    if not url:
        return None
    if _redis is None:
        try:
            import redis
            _redis = redis.Redis.from_url(url, socket_connect_timeout=1, decode_responses=True)
            _redis.ping()
        except Exception:
            _redis = False
    return _redis or None


def cache_get(key):
    r = _r()
    if r:
        try:
            v = r.get(PREFIX + key)
            return json.loads(v) if v else None
        except Exception:
            return None
    with _lock:
        hit = _local.get(key)
        if hit and hit[0] > time.time():
            return json.loads(hit[1])
    return None


def cache_set(key, value, ttl=600):
    s = json.dumps(value, default=str)
    r = _r()
    if r:
        try:
            r.setex(PREFIX + key, ttl, s)
            return
        except Exception:
            pass
    with _lock:
        _local[key] = (time.time() + ttl, s)


def cache_clear():
    """Invalidate everything after a new data import."""
    r = _r()
    if r:
        try:
            for k in r.scan_iter(PREFIX + "*"):
                r.delete(k)
        except Exception:
            pass
    with _lock:
        _local.clear()
