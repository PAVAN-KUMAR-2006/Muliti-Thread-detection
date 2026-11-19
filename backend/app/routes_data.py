import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select  # type: ignore[reportMissingImports]
from sqlalchemy.orm import Session  # type: ignore[reportMissingImports]
from . import models
from .database import get_db
from .deps import get_current_user, get_owned_scan

router = APIRouter(prefix="/api", tags=["data"])
HIGH = ("HIGH", "CRITICAL")
TYPES = ("website", "email", "message", "qr", "phone", "file")
LABELS = ("Safe", "Suspicious", "Spam", "Phishing", "Scam")
LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class ScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scan_type: str
    input_summary: str
    label: str
    risk_score: float
    risk_level: str
    status: str
    created_at: datetime


class HistoryPage(BaseModel):
    items: list[ScanSummary]
    total: int
    page: int
    limit: int
    total_pages: int


class IndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    severity: str
    weight: float


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model_name: str
    model_version: str
    probability: float


class EmailDetails(BaseModel):
    sender: str
    subject: str


class ScanDetail(ScanSummary):
    confidence: float | None
    explanation: str
    recommendation: str
    indicators: list[IndicatorOut]
    predictions: list[PredictionOut]
    email_details: EmailDetails | None = None


class ActivityPoint(BaseModel):
    date: str
    count: int


class Overview(BaseModel):
    total: int
    high_risk: int
    by_label: dict[str, int]
    by_level: dict[str, int]
    by_type: dict[str, int]
    activity_days: int
    activity: list[ActivityPoint]
    recent: list[ScanSummary]
    last_scan: ScanSummary | None
    state: str


THREAT_LABELS = ("Phishing", "Spam", "Scam")


def scan_conditions(user, q=None, type=None, threat=None, risk=None, date_from=None, date_to=None):
    """Single source of truth for history filtering. Always scoped to the signed-in user."""
    S = models.Scan
    conds = [S.user_id == user.id]  # enforced in the query, never only in the frontend
    if q:
        like = f"%{q}%"
        conds.append(or_(S.input_summary.ilike(like), S.label.ilike(like), S.scan_type.ilike(like)))
    if type: conds.append(S.scan_type == type.lower())
    if threat:
        t = threat.lower()
        if t == "high_risk": conds.append(S.risk_level.in_(HIGH))
        elif t == "threat": conds.append(S.label.in_(THREAT_LABELS))  # phishing, spam or scam
        else: conds.append(func.lower(S.label) == t)
    if risk: conds.append(S.risk_level == risk.upper())
    if date_from: conds.append(S.created_at >= date_from)
    if date_to: conds.append(S.created_at <= date_to)
    return conds


@router.get("/history", response_model=HistoryPage)
def history(q: str = Query("", max_length=200), type: str | None = None, threat: str | None = None,
            risk: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None,
            sort: Literal["newest", "oldest", "risk_desc", "risk_asc"] = "newest",
            page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50),
            user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    S = models.Scan
    conds = scan_conditions(user, q, type, threat, risk, date_from, date_to)
    order = {"newest": S.created_at.desc(), "oldest": S.created_at.asc(),
             "risk_desc": S.risk_score.desc(), "risk_asc": S.risk_score.asc()}[sort]
    total = db.scalar(select(func.count()).select_from(S).where(*conds)) or 0
    rows = db.scalars(select(S).where(*conds).order_by(order, S.id).offset((page - 1) * limit).limit(limit)).all()
    return HistoryPage(items=rows, total=total, page=page, limit=limit, total_pages=max(1, math.ceil(total / limit)))


@router.get("/history/{scan_id}", response_model=ScanDetail)
def history_item(scan_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_owned_scan(scan_id, user, db)  # 404 for missing or someone else's scan
    inds = db.scalars(select(models.ThreatIndicator).where(models.ThreatIndicator.scan_id == s.id).order_by(models.ThreatIndicator.weight.desc())).all()
    preds = db.scalars(select(models.ModelPrediction).where(models.ModelPrediction.scan_id == s.id)).all()
    email_details = None
    if s.scan_type == "email":
        e = db.get(models.EmailScan, s.id)  # primary key of email_scans is scan_id, which equals scans.id
        if e is not None:
            email_details = EmailDetails(sender=e.sender or "", subject=e.subject or "")
    base = ScanSummary.model_validate(s).model_dump()
    return ScanDetail(**base, confidence=s.confidence, explanation=s.explanation, recommendation=s.recommendation,
                      indicators=inds, predictions=preds, email_details=email_details)


@router.get("/dashboard/overview", response_model=Overview)
def overview(days: int = Query(30), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if days not in (7, 30, 90):
        raise HTTPException(422, "days must be 7, 30 or 90.")
    S = models.Scan
    own = S.user_id == user.id

    def group(col, keys, exclude_unknown_phone=False):
        filters = [own]
        if exclude_unknown_phone:
            filters.append(~((S.scan_type == "phone") & (S.label == "Unknown")))
        found = dict(db.execute(select(col, func.count()).where(*filters).group_by(col)).all())
        return {k: int(found.get(k, 0)) for k in keys}

    by_label = group(S.label, LABELS)
    by_level = group(S.risk_level, LEVELS, exclude_unknown_phone=True)
    by_type = group(S.scan_type, TYPES)
    total = db.scalar(select(func.count()).select_from(S).where(own)) or 0
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days - 1)).date()
    day = func.date(S.created_at)
    rows = db.execute(select(day, func.count()).where(own, S.created_at >= datetime.combine(start, datetime.min.time(), timezone.utc))
                      .group_by(day)).all()
    counts = {(datetime.fromisoformat(d).date() if isinstance(d, str) else d): c for d, c in rows}
    activity = [ActivityPoint(date=(start + timedelta(i)).isoformat(), count=counts.get(start + timedelta(i), 0)) for i in range(days)]
    recent = db.scalars(select(S).where(own).order_by(S.created_at.desc()).limit(6)).all()
    recent_high = db.scalar(select(func.count()).select_from(S).where(own, S.risk_level.in_(HIGH), S.created_at >= now - timedelta(days=7))) or 0
    if total == 0:
        state = "No data"
    elif recent_high:
        state = "Elevated"
    else:
        state = "Clear"
    return Overview(total=total, high_risk=by_level["HIGH"] + by_level["CRITICAL"], by_label=by_label, by_level=by_level,
                    by_type=by_type, activity_days=days, activity=activity, recent=recent,
                    last_scan=recent[0] if recent else None, state=state)
