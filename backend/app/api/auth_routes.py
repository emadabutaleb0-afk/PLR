from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
import jwt
from app.db.session import get_db
from app.core.security import verify_password, hash_password, access_token, refresh_token, decode
from app.models.app import User
from app.auth.deps import current_user, require
from app.auth.rbac import ROLES, ROLE_SCOPES
from app.services.audit import audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


def _user_dict(u: User):
    return dict(id=u.id, email=u.email, full_name=u.full_name, role=u.role, allowed_locations=u.allowed_locations, scopes=sorted(ROLE_SCOPES.get(u.role, [])),
                is_active=u.is_active, created_at=u.created_at.isoformat() if u.created_at else None)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    u = db.scalars(select(User).where(User.email == body.email.lower().strip())).first()
    if not u or not u.is_active or not verify_password(body.password, u.password_hash):
        audit(db, None, "login_failed", detail={"email_hint": body.email[:3] + "***"})
        raise HTTPException(401, "Email or password is not correct.")
    audit(db, u, "login")
    return TokenOut(access_token=access_token(u.id, u.role), refresh_token=refresh_token(u.id), user=_user_dict(u))


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    try:
        data = decode(body.refresh_token, "refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    except Exception:
        raise HTTPException(401, "Your session is not valid. Please sign in again.")
    u = db.get(User, int(data["sub"]))
    if not u or not u.is_active:
        raise HTTPException(401, "This account is not active.")
    return TokenOut(access_token=access_token(u.id, u.role), refresh_token=refresh_token(u.id), user=_user_dict(u))


@router.get("/me")
def me(u: User = Depends(current_user)):
    return _user_dict(u)


class UserIn(BaseModel):
    email: str
    full_name: str = ""
    password: str = Field(min_length=10)
    role: str
    allowed_locations: list[str] | None = None


_EMAIL = __import__("re").compile(r"^[^@\s]+@[^@\s]+$")


@router.get("/locations")
def locations(db: Session = Depends(get_db), admin: User = Depends(require("users_admin"))):
    from app.models.tables import TABLES
    lt = TABLES["locations"]
    return [dict(location_id=r.location_id, location_name=r.location_name) for r in db.execute(select(lt.c.location_id, lt.c.location_name).order_by(lt.c.location_id))]


@router.post("/users", status_code=201)
def create_user(body: UserIn, db: Session = Depends(get_db), admin: User = Depends(require("users_admin"))):
    if not _EMAIL.match(body.email.strip()):
        raise HTTPException(422, "Please enter a valid email address.")
    if body.role not in ROLES:
        raise HTTPException(422, f"Role must be one of: {', '.join(ROLES)}")
    if body.role == "STORE_MANAGER" and not body.allowed_locations:
        raise HTTPException(422, "A store manager needs at least one allowed location.")
    if db.scalars(select(User).where(User.email == body.email.lower())).first():
        raise HTTPException(409, "A user with this email already exists.")
    u = User(email=body.email.lower().strip(), full_name=body.full_name, password_hash=hash_password(body.password), role=body.role, allowed_locations=body.allowed_locations)
    db.add(u); db.commit()
    audit(db, admin, "user_created", "user", str(u.id), {"role": u.role})
    return _user_dict(u)


class UserPatch(BaseModel):
    full_name: str | None = None
    role: str | None = None
    allowed_locations: list[str] | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=10, description="Admin password reset")


def _active_ceos(db: Session) -> int:
    return len(db.scalars(select(User).where(User.role == "CEO", User.is_active == True)).all())  # noqa: E712


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserPatch, db: Session = Depends(get_db), admin: User = Depends(require("users_admin"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found.")
    if body.role is not None and body.role not in ROLES:
        raise HTTPException(422, f"Role must be one of: {', '.join(ROLES)}")
    new_role = body.role or u.role
    new_active = u.is_active if body.is_active is None else body.is_active
    if u.role == "CEO" and (new_role != "CEO" or not new_active) and _active_ceos(db) <= 1:
        raise HTTPException(409, "There must always be at least one active CEO account.")
    if new_role == "STORE_MANAGER" and not (body.allowed_locations if body.allowed_locations is not None else u.allowed_locations):
        raise HTTPException(422, "A store manager needs at least one allowed location.")
    if body.full_name is not None: u.full_name = body.full_name.strip()
    if body.role is not None: u.role = body.role
    if body.allowed_locations is not None: u.allowed_locations = body.allowed_locations or None
    if body.is_active is not None: u.is_active = body.is_active
    if body.password: u.password_hash = hash_password(body.password)
    db.commit()
    audit(db, admin, "user_updated", "user", str(u.id), {"fields": [k for k, v in body.model_dump().items() if v is not None and k != "password"], "password_reset": bool(body.password)})
    return _user_dict(u)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)


@router.post("/change-password")
def change_password(body: PasswordIn, db: Session = Depends(get_db), u: User = Depends(current_user)):
    if not verify_password(body.current_password, u.password_hash):
        raise HTTPException(422, "Your current password is not correct.")
    if body.new_password == body.current_password:
        raise HTTPException(422, "Choose a password that is different from the current one.")
    u.password_hash = hash_password(body.new_password)
    db.commit()
    audit(db, u, "password_changed")
    return {"ok": True}


@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require("users_admin"))):
    return [_user_dict(u) for u in db.scalars(select(User).order_by(User.id))]
