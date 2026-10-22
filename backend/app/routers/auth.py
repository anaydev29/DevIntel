"""Google sign-in (OpenID Connect authorization-code flow via Authlib) and the login session.

We ask Google only for the basic sign-in scopes (openid, email, profile) and keep the user's id in a
signed, HttpOnly cookie. No passwords are ever handled or stored.
"""
from datetime import datetime, timezone

from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import MeOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def google_enabled() -> bool:
    return oauth.create_client("google") is not None


def user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, name=u.name, avatar_url=u.avatar_url,
                   github_username=u.github_username, role=u.role)


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    return db.get(User, user_id) if user_id else None


def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(401, "Sign in to do this")
    return user


def upsert_google_user(db: Session, info: dict) -> User:
    """Find the user by Google's stable id (never by email) or create them; refresh basic details."""
    user = db.scalar(select(User).where(User.google_sub == info["sub"]))
    if user is None:
        user = User(google_sub=info["sub"], email=info["email"])
        db.add(user)
    user.email = info["email"]
    user.name = info.get("name")
    user.avatar_url = info.get("picture")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user


@router.get("/google/login")
async def google_login(request: Request):
    client = oauth.create_client("google")
    if client is None:
        raise HTTPException(503, "Google login is not configured on this server")
    if settings.public_base_url:
        redirect_uri = f"{settings.public_base_url.rstrip('/')}/auth/google/callback"
    else:
        redirect_uri = str(request.url_for("google_callback"))
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    client = oauth.create_client("google")
    if client is None:
        raise HTTPException(503, "Google login is not configured on this server")
    try:
        token = await client.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse("/?login=failed")
    info = token.get("userinfo") or {}
    if not info.get("sub") or not info.get("email") or not info.get("email_verified"):
        return RedirectResponse("/?login=failed")
    user = upsert_google_user(db, info)
    request.session.clear()                      # fresh session after login
    request.session["user_id"] = user.id
    return RedirectResponse("/")


@router.get("/me", response_model=MeOut)
def me(user: User | None = Depends(current_user)):
    return MeOut(authenticated=user is not None, login_enabled=google_enabled(),
                 user=user_out(user) if user else None)


@router.post("/logout", status_code=204)
def logout(request: Request):
    request.session.clear()
    return Response(status_code=204)
