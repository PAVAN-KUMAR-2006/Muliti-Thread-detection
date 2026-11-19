import uuid
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models, security as sec
from .database import get_db

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> models.User:
    unauthorized = HTTPException(401, "Your session has expired. Sign in again.", headers={"WWW-Authenticate": "Bearer"})
    payload = sec.decode(creds.credentials, "access") if creds else None
    if not payload:
        raise unauthorized
    try:
        user = db.get(models.User, uuid.UUID(payload["sub"]))
    except ValueError:
        raise unauthorized
    if not user or not user.is_active:
        raise unauthorized
    return user


def get_owned_scan(scan_id: uuid.UUID, user: models.User, db: Session) -> models.Scan:
    """Every scan lookup in later phases goes through here: filtered by user_id, 404 otherwise."""
    scan = db.scalar(select(models.Scan).where(models.Scan.id == scan_id, models.Scan.user_id == user.id))
    if not scan:
        raise HTTPException(404, "Scan not found.")
    return scan
