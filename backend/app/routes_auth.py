import logging
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from . import models, schemas, security as sec
from .config import settings
from .database import get_db
from .deps import get_current_user

log = logging.getLogger("auth")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def issue_tokens(db: Session, user: models.User, request: Request) -> schemas.TokenOut:
    refresh, exp = sec.make_refresh(str(user.id))
    db.add(models.AuthSession(user_id=user.id, token_hash=sec.sha(refresh), expires_at=exp,
                              user_agent=(request.headers.get("user-agent") or "")[:255]))
    db.commit()
    return schemas.TokenOut(access_token=sec.make_access(str(user.id)), refresh_token=refresh,
                            user=schemas.UserOut.model_validate(user))


@router.post("/register", response_model=schemas.TokenOut, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, body: schemas.RegisterIn, db: Session = Depends(get_db)):
    user = models.User(name=body.name, email=body.email.lower(), password_hash=sec.hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists. Sign in instead.")
    return issue_tokens(db, user, request)


@router.post("/login", response_model=schemas.TokenOut)
@limiter.limit("10/minute")
def login(request: Request, body: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == body.email.lower()))
    valid = sec.verify_password(body.password, user.password_hash if user else sec.DUMMY)
    if not user or not valid or not user.is_active:
        raise HTTPException(401, "Incorrect email or password.")
    return issue_tokens(db, user, request)


@router.post("/refresh", response_model=schemas.TokenOut)
@limiter.limit("30/minute")
def refresh(request: Request, body: schemas.RefreshIn, db: Session = Depends(get_db)):
    invalid = HTTPException(401, "Your session has expired. Sign in again.")
    payload = sec.decode(body.refresh_token, "refresh")
    if not payload:
        raise invalid
    session = db.scalar(select(models.AuthSession).where(models.AuthSession.token_hash == sec.sha(body.refresh_token)))
    if not session or session.revoked or session.expires_at < datetime.now(timezone.utc):
        raise invalid
    user = db.get(models.User, session.user_id)
    if not user or not user.is_active:
        raise invalid
    session.revoked = True  # rotation: each refresh token works once
    return issue_tokens(db, user, request)


@router.post("/logout", status_code=204)
@limiter.limit("30/minute")
def logout(request: Request, body: schemas.RefreshIn, db: Session = Depends(get_db)):
    db.execute(update(models.AuthSession).where(models.AuthSession.token_hash == sec.sha(body.refresh_token)).values(revoked=True))
    db.commit()


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, body: schemas.ForgotIn, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == body.email.lower()))
    if user:
        raw = secrets.token_urlsafe(32)
        db.add(models.PasswordReset(user_id=user.id, token_hash=sec.sha(raw),
                                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.reset_minutes)))
        db.commit()
        # No mail server is configured yet, so the link is written to the backend log.
        log.warning("PASSWORD RESET LINK for %s: %s/reset-password?token=%s", user.email, settings.frontend_url, raw)
    return {"message": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(request: Request, body: schemas.ResetIn, db: Session = Depends(get_db)):
    reset = db.scalar(select(models.PasswordReset).where(
        models.PasswordReset.token_hash == sec.sha(body.token), models.PasswordReset.used.is_(False),
        models.PasswordReset.expires_at > datetime.now(timezone.utc)))
    if not reset:
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.")
    user = db.get(models.User, reset.user_id)
    user.password_hash = sec.hash_password(body.password)
    reset.used = True
    db.execute(update(models.AuthSession).where(models.AuthSession.user_id == user.id).values(revoked=True))
    db.commit()
    return {"message": "Password updated. Sign in with your new password."}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
