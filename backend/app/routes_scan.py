
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import models
from .database import get_db
from .deps import get_current_user
from .ml import service
from .ml.features import (
    LABELS,
    find_urls,
    language_signals,
    normalize_url,
    url_features,
)
from .routes_auth import limiter
from .routes_data import IndicatorOut, ScanDetail, ScanSummary


router = APIRouter(prefix="/api/scan", tags=["scan"])

RECOMMEND = {
    "Safe": "No threat was indicated. Stay cautious with unexpected requests for personal information.",
    "Suspicious": "Do not click links or share details until you confirm the sender or site through an official channel.",
    "Spam": "Do not reply or click anything. Delete or report the message.",
    "Phishing": "Do not open the link or enter credentials. Report it and, if you already interacted, change your passwords.",
    "Scam": "Do not respond or send money or codes. Block the sender and report the message.",
}

NOT_TRAINED = (
    "The {} model has not been trained yet. "
    "Run its training script in ml/training, then try again."
)


class ScanResult(ScanDetail):
    protective: list[IndicatorOut]
    details: dict = {}


def level_of(score: float) -> str:
    if score > 80:
        return "CRITICAL"
    if score > 60:
        return "HIGH"
    if score > 30:
        return "MEDIUM"
    return "LOW"


def sev(w: float) -> str:
    if w > 0.66:
        return "high"
    if w > 0.33:
        return "medium"
    return "low"


def split_contrib(contrib, k=6):
    raising = [(n, d) for n, d in contrib if d > 0][:k]
    lowering = [(n, d) for n, d in contrib if d < 0][:3]

    top = max([d for _, d in raising] + [1e-9])

    return (
        [
            IndicatorOut(
                name=n,
                severity=sev(d / top),
                weight=round(d / top, 3),
            )
            for n, d in raising
        ],
        [
            IndicatorOut(
                name=n,
                severity="low",
                weight=round(
                    abs(d) / max(abs(x) for _, x in lowering),
                    3,
                ),
            )
            for n, d in lowering
        ],
    )


def explain(label, p, kind, raising):
    why = "; ".join(i.name for i in raising[:3]) or (
        "no individual factor stood out"
    )
    return (
        f"The {kind} model rated this {p:.0%} likely to be malicious, "
        f"classified as {label}. Main contributing factors: {why}."
    )


def save_scan(
    db,
    user,
    scan_type,
    summary,
    label,
    p,
    model_name,
    indicators,
    protective,
    kind,
    detail,
    prediction_options=None,
):
    prediction_options = prediction_options or {}
    details = prediction_options.get("details")
    extra_preds = prediction_options.get("extra_preds", ())
    primary_p = prediction_options.get("primary_p")
    score = round(p * 100, 1)

    scan = models.Scan(
        user_id=user.id,
        scan_type=scan_type,
        input_summary=summary[:500],
        label=label,
        risk_score=score,
        risk_level=level_of(score),
        confidence=round(max(p, 1 - p), 4),
        status="completed",
        explanation=explain(label, p, kind, indicators),
        recommendation=RECOMMEND[label],
    )

    db.add(scan)
    db.flush()

    # Save scan-specific details.
    db.add(detail(scan.id))

    # Save threat indicators.
    for i in indicators:
        db.add(
            models.ThreatIndicator(
                scan_id=scan.id,
                name=i.name[:120],
                severity=i.severity,
                weight=i.weight,
            )
        )

    # Save the primary model prediction.
    db.add(
        models.ModelPrediction(
            scan_id=scan.id,
            model_name=model_name,
            model_version=service.bundle(model_name)["meta"]["version"],
            probability=p if primary_p is None else primary_p,
        )
    )

    # Save additional model predictions.
    for n, q in extra_preds:
        db.add(
            models.ModelPrediction(
                scan_id=scan.id,
                model_name=n,
                model_version=service.bundle(n)["meta"]["version"],
                probability=q,
            )
        )

    # Notify the user about high-risk scans.
    if scan.risk_level in ("HIGH", "CRITICAL"):
        db.add(
            models.Notification(
                user_id=user.id,
                title="High-risk threat detected",
                body=f"{label}: {summary[:150]}",
            )
        )

    db.commit()

    return ScanResult(
        **ScanSummary.model_validate(scan).model_dump(),
        confidence=scan.confidence,
        explanation=scan.explanation,
        recommendation=scan.recommendation,
        indicators=indicators,
        predictions=[],
        protective=protective,
        details=details or {},
    )


class UrlIn(BaseModel):
    url: str = Field(min_length=3, max_length=2048)


class EmailIn(BaseModel):
    sender: str = Field("", max_length=320)
    subject: str = Field("", max_length=500)
    body: str = Field(min_length=3, max_length=50000)


class MessageIn(BaseModel):
    text: str = Field(min_length=2, max_length=5000)
    platform: str = Field("sms", max_length=32)


def url_details(url):
    p = urlparse(url)

    return {
        "url": url,
        "host": p.hostname,
        "scheme": p.scheme,
        "https": p.scheme == "https",
        "features": {
            LABELS[k]: round(v, 3)
            for k, v in url_features(url).items()
        },
    }


def url_analysis(raw):
    """The single URL analysis service: used by the website, QR, email, message and file scanners."""
    url = normalize_url(raw)
    host = urlparse(url).hostname

    if (
        not host
        or (" " in raw.strip())
        or ("." not in host and ":" not in host)
    ):
        raise HTTPException(
            422,
            "Enter a valid URL, for example https://example.com.",
        )

    # The URL is analysed as text only; it is never fetched.
    res = service.predict_url(url)

    if res is None:
        raise HTTPException(
            503,
            NOT_TRAINED.format("website"),
        )

    p, contrib = res

    if p >= 0.5:
        label = "Phishing"
    elif p >= 0.3:
        label = "Suspicious"
    else:
        label = "Safe"

    ind, prot = split_contrib(contrib)

    return url, p, label, ind, prot, contrib


@router.post(
    "/website",
    response_model=ScanResult,
    responses={
        422: {"description": "Invalid URL"},
        503: {"description": "URL model not trained or unavailable"},
    },
)
@limiter.limit("30/minute")
def scan_website(
    request: Request,
    body: UrlIn,
    user: models.User = Depends(get_current_user),
    db=Depends(get_db),
):
    url, p, label, ind, prot, contrib = url_analysis(body.url)

    return save_scan(
        db,
        user,
        "website",
        url,
        label,
        p,
        "url_phishing_model",
        ind,
        prot,
        "URL",
        lambda sid: models.WebsiteScan(
            scan_id=sid,
            url=url,
            features=dict(contrib),
        ),
        prediction_options={"details": url_details(url)},
    )


def classify_text(p, kind, flagged):
    if p < 0.3:
        return "Safe"
    if p < 0.5:
        return "Suspicious"
    if flagged:
        return "Phishing" if kind == "email" else "Scam"
    return "Spam"


def text_scan(
    db,
    user,
    scan_type,
    model_name,
    text,
    summary,
    kind,
    detail,
    extra_ind=(),
    extra_details=None,
):
    """Shared text pipeline (email, message, file): text model + URL service on every link found."""

    res = service.predict_text(model_name, text)

    if res is None:
        raise HTTPException(
            503,
            NOT_TRAINED.format(model_name.replace("_model", "")),
        )

    p_text, contrib = res

    ind, prot = split_contrib(
        [(f'Term "{n}"', d) for n, d in contrib]
    )

    urls = []

    for u in find_urls(text):
        r = service.predict_url(u)

        urls.append(
            {
                "url": u,
                "phishing_probability": round(r[0], 4) if r else None,
            }
        )

    scored = [
        x["phishing_probability"]
        for x in urls
        if x["phishing_probability"] is not None
    ]

    flagged = [
        x for x in urls
        if (x["phishing_probability"] or 0) >= 0.5
    ]

    for x in flagged:
        ind.insert(
            0,
            IndicatorOut(
                name=(
                    f"Linked URL rated "
                    f"{x['phishing_probability']:.0%} phishing: "
                    f"{urlparse(normalize_url(x['url'])).hostname}"
                ),
                severity="high",
                weight=x["phishing_probability"],
            ),
        )

    ind += [
        IndicatorOut(name=n, severity="low", weight=0.25)
        for n in language_signals(text)
    ] + list(extra_ind)

    # Overall risk uses the highest text or linked-URL score.
    p = max([p_text] + scored)

    label = classify_text(p, kind, bool(flagged))

    return save_scan(
        db,
        user,
        scan_type,
        summary,
        label,
        p,
        model_name,
        ind,
        prot,
        kind,
        detail,
        prediction_options={
            "details": {
                "urls": urls,
                "text_probability": round(p_text, 4),
                **(extra_details or {}),
            },
            "extra_preds": [
                ("url_phishing_model", max(scored))
            ] if scored else [],
            "primary_p": p_text,
        },
    )


@router.post(
    "/email",
    response_model=ScanResult,
    responses={503: {"description": "Email model not trained or unavailable"}},
)
@limiter.limit("30/minute")
def scan_email(
    request: Request,
    body: EmailIn,
    user: models.User = Depends(get_current_user),
    db=Depends(get_db),
):
    sender = body.sender.strip()[:320]
    subject = body.subject.strip()[:500]
    text = f"{subject} {body.body}"

    return text_scan(
        db,
        user,
        "email",
        "email_model",
        text,
        subject or body.body[:200],
        "email",
        lambda sid: models.EmailScan(
            scan_id=sid,
            sender=sender,
            subject=subject,
            body_excerpt=body.body[:2000],
        ),
        extra_details={
            "sender": sender,
            "subject": subject,
        },
    )


@router.post(
    "/message",
    response_model=ScanResult,
    responses={503: {"description": "Message model not trained or unavailable"}},
)
@limiter.limit("30/minute")
def scan_message(
    request: Request,
    body: MessageIn,
    user: models.User = Depends(get_current_user),
    db=Depends(get_db),
):
    return text_scan(
        db,
        user,
        "message",
        "sms_model",
        body.text,
        body.text[:300],
        "message",
        lambda sid: models.MessageScan(
            scan_id=sid,
            platform=body.platform,
            text=body.text,
        ),
    )
