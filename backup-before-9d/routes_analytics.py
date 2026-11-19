"""Analytics. Every query is scoped to the authenticated user (never to a user id supplied by the client) and all
aggregation (COUNT / GROUP BY / date_trunc) runs in PostgreSQL. Days are UTC calendar days."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from . import models
from .database import get_db
from .deps import get_current_user
from .routes_data import HIGH, LABELS, LEVELS, THREAT_LABELS, TYPES

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
S = models.Scan
CARD_KEYS = ("total", "safe", "suspicious", "threats", "high", "critical")
CHANNELS = ("website", "email", "message", "qr", "file")


@dataclass
class Window:
    start: datetime   # inclusive
    end: datetime     # exclusive
    days: int
    scanner: str | None


def get_window(days: Literal[7, 30, 90] | None = None, date_from: date | None = None, date_to: date | None = None,
               scanner: str | None = None) -> Window:
    if scanner is not None and scanner not in TYPES:
        raise HTTPException(422, "Unknown scanner type.")
    if date_from or date_to:
        if not (date_from and date_to):
            raise HTTPException(422, "Choose both a start date and an end date.")
        if date_from > date_to:
            raise HTTPException(422, "The start date must not be after the end date.")
        if (date_to - date_from).days >= 366:
            raise HTTPException(422, "The date range can be at most 366 days.")
        start_d, end_d = date_from, date_to + timedelta(days=1)
    else:
        n = days or 30
        end_d = datetime.now(timezone.utc).date() + timedelta(days=1)  # include today
        start_d = end_d - timedelta(days=n)
    start, end = (datetime.combine(d, time.min, timezone.utc) for d in (start_d, end_d))
    return Window(start, end, (end - start).days, scanner)


def conds(user: models.User, w: Window, start=None, end=None, use_scanner=True):
    c = [S.user_id == user.id, S.created_at >= (start or w.start), S.created_at < (end or w.end)]
    if use_scanner and w.scanner:
        c.append(S.scan_type == w.scanner)
    return c


def totals(db: Session, c) -> dict[str, int]:
    row = db.execute(select(
        func.count(), func.count().filter(S.label == "Safe"), func.count().filter(S.label == "Suspicious"),
        func.count().filter(S.label.in_(THREAT_LABELS)), func.count().filter(S.risk_level == "HIGH"),
        func.count().filter(S.risk_level == "CRITICAL")).where(*c)).one()
    return dict(zip(CARD_KEYS, (int(x) for x in row)))


def per_day(db: Session, c, *cols):
    day = func.date_trunc("day", func.timezone("UTC", S.created_at))
    rows = db.execute(select(day, *cols).where(*c).group_by(day)).all()
    return {r[0].date(): r[1:] for r in rows}


def window_days(w: Window) -> list[date]:
    return [w.start.date() + timedelta(i) for i in range(w.days)]


def grouped(db, c, col, keys):
    found = dict(db.execute(select(col, func.count()).where(*c).group_by(col)).all())
    items = [{"name": k, "count": int(found.get(k, 0))} for k in keys]
    items += [{"name": k, "count": int(v)} for k, v in found.items() if k not in keys]
    return {"items": items, "total": sum(i["count"] for i in items)}


@router.get("/overview")
def overview(w: Window = Depends(get_window), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    cur = totals(db, conds(user, w))
    prev = totals(db, conds(user, w, w.start - timedelta(days=w.days), w.start))  # the equally long period before
    card = lambda k: {"value": cur[k], "previous": prev[k],
                      "change_pct": round((cur[k] - prev[k]) / prev[k] * 100, 1) if prev[k] else None}
    total_ever = db.scalar(select(func.count()).select_from(S).where(S.user_id == user.id)) or 0
    return {"range": {"start": w.start.date().isoformat(), "end": (w.end - timedelta(days=1)).date().isoformat(), "days": w.days},
            "scanner": w.scanner, "total_ever": total_ever, "comparison_available": prev["total"] > 0,
            "cards": {k: card(k) for k in CARD_KEYS}}


@router.get("/scanner-usage")
def scanner_usage(w: Window = Depends(get_window), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return grouped(db, conds(user, w, use_scanner=False), S.scan_type, CHANNELS)  # the scanner filter would defeat this chart


@router.get("/threat-distribution")
def threat_distribution(w: Window = Depends(get_window), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return grouped(db, conds(user, w), S.label, LABELS)


@router.get("/risk-distribution")
def risk_distribution(w: Window = Depends(get_window), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return grouped(db, conds(user, w), S.risk_level, LEVELS)


@router.get("/scan-trends")
def scan_trends(w: Window = Depends(get_window), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    counts = per_day(db, conds(user, w), func.count())
    points = [{"date": d.isoformat(), "count": int(counts[d][0]) if d in counts else 0} for d in window_days(w)]
    return {"points": points, "total": sum(p["count"] for p in points)}


@router.get("/threat-trends")
def threat_trends(w: Window = Depends(get_window), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = per_day(db, conds(user, w) + [S.label.in_(THREAT_LABELS)],
                   func.count().filter(S.label == "Phishing"), func.count().filter(S.label == "Spam"), func.count().filter(S.label == "Scam"))
    points = [{"date": d.isoformat(), "phishing": int(rows[d][0]) if d in rows else 0,
               "spam": int(rows[d][1]) if d in rows else 0, "scam": int(rows[d][2]) if d in rows else 0} for d in window_days(w)]
    return {"points": points, "total": sum(p["phishing"] + p["spam"] + p["scam"] for p in points),
            "sufficient": len(rows) >= 2}  # a trend needs detections on at least two different days


@router.get("/high-risk")
def high_risk(w: Window = Depends(get_window), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(S).where(*conds(user, w), S.risk_level.in_(HIGH)).order_by(S.created_at.desc()).limit(8)).all()
    return {"items": [{"id": str(s.id), "scan_type": s.scan_type, "label": s.label, "risk_score": s.risk_score,
                       "risk_level": s.risk_level, "created_at": s.created_at.isoformat(),
                       "explanation": (s.explanation or "")[:180]} for s in rows]}
