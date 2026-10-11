from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode
from app.models.app import User
from app.auth.rbac import ROLE_SCOPES, COST_FIELDS

bearer = HTTPBearer(auto_error=False)


def current_user(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Please sign in to continue.")
    try:
        data = decode(creds.credentials, "access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    except Exception:
        raise HTTPException(401, "Your session is not valid. Please sign in again.")
    u = db.get(User, int(data["sub"]))
    if not u or not u.is_active:
        raise HTTPException(401, "This account is not active.")
    request.state.user = u
    return u


def require(scope: str):
    def dep(u: User = Depends(current_user)) -> User:
        if scope not in ROLE_SCOPES.get(u.role, set()):
            raise HTTPException(403, f"Your role ({u.role.replace('_', ' ').title()}) does not have access to this area.")
        return u
    return dep


def has(u: User, scope: str) -> bool:
    return scope in ROLE_SCOPES.get(u.role, set())


def scope_rows(u: User, rows: list[dict], loc_key="location_id") -> list[dict]:
    """Row-level isolation: store managers only see their allowed locations; rows with no location are hidden from them."""
    if u.role == "STORE_MANAGER":
        allowed = set(u.allowed_locations or [])
        return [r for r in rows if r.get(loc_key) in allowed]
    return rows


def strip_fields(u: User, obj):
    """Column-level isolation: remove cost/margin fields for roles without the 'costs' scope."""
    if has(u, "costs"):
        return obj
    if isinstance(obj, list):
        return [strip_fields(u, o) for o in obj]
    if isinstance(obj, dict):
        return {k: strip_fields(u, v) for k, v in obj.items() if k not in COST_FIELDS}
    return obj
