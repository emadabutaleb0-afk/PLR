from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from app.core.config import get_settings

ALGO = "HS256"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except Exception:
        return False


def _token(sub: str, kind: str, delta: timedelta, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "type": kind, "iat": now, "exp": now + delta, **(extra or {})}
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGO)


def access_token(user_id: int, role: str) -> str:
    return _token(str(user_id), "access", timedelta(minutes=get_settings().access_token_minutes), {"role": role})


def refresh_token(user_id: int) -> str:
    return _token(str(user_id), "refresh", timedelta(days=get_settings().refresh_token_days))


def decode(token: str, kind: str) -> dict:
    data = jwt.decode(token, get_settings().secret_key, algorithms=[ALGO])
    if data.get("type") != kind:
        raise jwt.InvalidTokenError("wrong token type")
    return data
