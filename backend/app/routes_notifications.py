"""Notifications. Every query is filtered by the authenticated user's id; another user's notification id returns 404."""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from . import models
from .database import get_db
from .deps import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
N = models.Notification


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
    read: bool
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unread_count: int


@router.get("", response_model=NotificationList)
def list_notifications(unread_only: bool = False, limit: int = Query(20, ge=1, le=50),
                       user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    conds = [N.user_id == user.id]
    if unread_only:
        conds.append(N.read.is_(False))
    items = db.scalars(select(N).where(*conds).order_by(N.created_at.desc()).limit(limit)).all()
    unread = db.scalar(select(func.count()).select_from(N).where(N.user_id == user.id, N.read.is_(False))) or 0
    return NotificationList(items=items, unread_count=unread)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.scalar(select(N).where(N.id == notification_id, N.user_id == user.id))
    if not n:
        raise HTTPException(404, "Notification not found.")
    n.read = True
    db.commit()
    return n


@router.post("/read-all")
def mark_all_read(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    res = db.execute(update(N).where(N.user_id == user.id, N.read.is_(False)).values(read=True))
    db.commit()
    return {"updated": res.rowcount}
