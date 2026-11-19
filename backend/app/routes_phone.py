"""Phone threat module API. Every query is scoped to the authenticated user where private, and reporter identities are
never returned. Phone scans are ordinary rows in `scans` (scan_type = 'phone'), so history, dashboard, analytics and exports
include them. This module deliberately does not use save_scan(): there is no ML model for phone numbers."""
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, phone_service as ps
from .database import get_db
from .deps import get_current_user, get_owned_scan
from .routes_auth import limiter

router = APIRouter(prefix="/api/phone", tags=["phone"])
DAILY_REPORT_CAP = 20
Category = Literal["Spam Call", "Financial Scam", "Banking Fraud", "OTP Scam", "Impersonation", "Robocall", "Telemarketing", "Other"]


def clean_text(value: str | None) -> str:
    """Strip HTML tags and control characters and collapse whitespace. The frontend also escapes on display."""
    value = re.sub(r"<[^>]*>", " ", value or "")
    value = re.sub(r"[\x00-\x1f\x7f]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


class ScanIn(BaseModel):
    number: str = Field(max_length=32)
    region: str | None = Field(None, max_length=2)


class ReportIn(BaseModel):
    number: str = Field(max_length=32)
    region: str | None = Field(None, max_length=2)
    category: Category
    description: str = Field(max_length=2000)
    evidence: str | None = Field(None, max_length=1000)

    @field_validator("description")
    @classmethod
    def _description(cls, v: str) -> str:
        v = clean_text(v)
        if not 10 <= len(v) <= 1000:
            raise ValueError("Describe what happened in 10 to 1000 characters.")
        return v

    @field_validator("evidence")
    @classmethod
    def _evidence(cls, v: str | None) -> str | None:
        v = clean_text(v)
        if len(v) > 500:
            raise ValueError("Evidence or reference must be 500 characters or fewer.")
        return v or None


class IndicatorOut(BaseModel):
    name: str
    severity: str
    weight: float


class PhoneScanOut(BaseModel):
    id: uuid.UUID
    scan_type: str
    label: str
    classification: str
    risk_score: float | None      # None when the number could not be scored (no evidence)
    risk_level: str | None
    status: str
    created_at: datetime
    explanation: str
    recommendation: str
    indicators: list[IndicatorOut]
    details: dict


class ReportOut(BaseModel):
    id: uuid.UUID
    number_display: str
    category: str
    description: str
    evidence: str | None
    created_at: datetime


def to_report(r: models.PhoneReport) -> ReportOut:
    return ReportOut(id=r.id, number_display=ps.display_from_e164(r.number), category=r.category, description=r.description,
                     evidence=r.evidence, created_at=r.created_at)


def parse_or_422(number: str, region: str | None) -> ps.Normalized:
    try:
        return ps.normalize(number, region)
    except ps.PhoneError as e:
        raise HTTPException(422, str(e))


@router.get("/regions")
def list_regions(user: models.User = Depends(get_current_user)):
    return [{"region": r, "dial_code": f"+{c}"} for r, c in ps.regions()]


@router.post("/scan", response_model=PhoneScanOut)
@limiter.limit("30/minute")
def scan_phone(request: Request, body: ScanIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    num = parse_or_422(body.number, body.region)
    now = datetime.now(timezone.utc)
    rows = db.execute(select(models.PhoneReport.category, models.PhoneReport.reported_by, models.PhoneReport.created_at)
                      .where(models.PhoneReport.number == num.e164)).all()
    ev = ps.evidence_from_rows(rows, now)
    a = ps.assess(ev, now)
    scan = models.Scan(user_id=user.id, scan_type="phone", input_summary=num.display, label=a.label, risk_score=a.score, risk_level=a.level,
                       confidence=None, status="completed", explanation=a.explanation, recommendation=a.recommendation)
    db.add(scan)
    db.flush()
    db.add(models.PhoneScan(scan_id=scan.id, number_e164=num.e164, region=num.region, country_code=num.country_code,
                            number_type=num.number_type, display=num.display))
    for name, severity, weight in a.indicators:
        db.add(models.ThreatIndicator(scan_id=scan.id, name=name[:120], severity=severity, weight=weight))
    if a.level in ("HIGH", "CRITICAL"):
        db.add(models.Notification(user_id=user.id, title="High-risk phone number", body=f"{num.display}: {a.classification}"))
    db.commit()
    details = {
        "number_display": num.display, "normalized": num.e164, "region": num.region, "country_code": f"+{num.country_code}",
        "number_type": num.number_type, "format_valid": True, "scored": a.scored, "evidence_level": a.evidence_level,
        "intel_source": "Sentinel community reports (local); no external threat-intelligence provider configured", "external_intel": False,
        "evidence": {"reports": ev.total, "reporters": ev.reporters, "categories": dict(ev.categories), "reports_30d": ev.within_30,
                     "reports_90d": ev.within_90, "last_report_days_ago": max(0, (now - ev.last_report).days) if ev.last_report else None},
        "score_breakdown": a.breakdown,
    }
    return PhoneScanOut(id=scan.id, scan_type="phone", label=a.label, classification=a.classification,
                        risk_score=a.score if a.scored else None, risk_level=a.level if a.scored else None, status="completed",
                        created_at=scan.created_at, explanation=a.explanation, recommendation=a.recommendation,
                        indicators=[IndicatorOut(name=n, severity=s, weight=w) for n, s, w in a.indicators], details=details)


@router.get("/scans/{scan_id}")
def phone_scan_details(scan_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    scan = get_owned_scan(scan_id, user, db)  # 404 for a missing scan or someone else's
    p = db.get(models.PhoneScan, scan.id) if scan.scan_type == "phone" else None
    if p is None:
        raise HTTPException(404, "Scan not found.")
    return {"scan_id": str(scan.id), "number_display": p.display, "normalized": p.number_e164, "region": p.region,
            "country_code": f"+{p.country_code}", "number_type": p.number_type, "created_at": scan.created_at.isoformat()}


@router.post("/reports", response_model=ReportOut, status_code=201)
@limiter.limit("10/hour")
def create_report(request: Request, body: ReportIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    num = parse_or_422(body.number, body.region)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    today = db.scalar(select(func.count()).select_from(models.PhoneReport)
                      .where(models.PhoneReport.reported_by == user.id, models.PhoneReport.created_at >= since)) or 0
    if today >= DAILY_REPORT_CAP:
        raise HTTPException(429, "You have reached the daily limit for reports. Try again tomorrow.")
    report = models.PhoneReport(number=num.e164, category=body.category, description=body.description, evidence=body.evidence,
                                region=num.region, reported_by=user.id)
    db.add(report)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already reported this number in this category.")
    return to_report(report)


@router.get("/reports", response_model=list[ReportOut])
def my_reports(limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0), user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    rows = db.scalars(select(models.PhoneReport).where(models.PhoneReport.reported_by == user.id)
                      .order_by(models.PhoneReport.created_at.desc(), models.PhoneReport.id).limit(limit).offset(offset)).all()
    return [to_report(r) for r in rows]


@router.get("/reports/{report_id}", response_model=ReportOut)
def my_report(report_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.scalar(select(models.PhoneReport).where(models.PhoneReport.id == report_id, models.PhoneReport.reported_by == user.id))
    if r is None:
        raise HTTPException(404, "Report not found.")
    return to_report(r)
