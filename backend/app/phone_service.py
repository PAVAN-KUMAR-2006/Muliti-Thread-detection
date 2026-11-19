"""Phone number analysis: format validation with libphonenumber plus transparent local rules over community reports.

Nothing here calls, texts or contacts a number, and nothing makes a network request. A valid number is not a safe
number and an unknown number is not a safe number: with no reports the result is "No known threat" and it is NOT scored.

Extension point: a real threat-intelligence provider can later be added by writing a function that returns an
`Evidence` object for a number and merging it in routes_phone.py. Its API key would come from an environment variable
read through app.config, never from source code. No provider is configured today."""
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat, PhoneNumberType

CATEGORIES = ("Spam Call", "Financial Scam", "Banking Fraud", "OTP Scam", "Impersonation", "Robocall", "Telemarketing", "Other")
HIGH_SEVERITY = frozenset({"Financial Scam", "Banking Fraud", "OTP Scam", "Impersonation"})

# The complete scoring rule set. These exact numbers are also returned to the user as the score breakdown.
POINTS_PER_REPORTER, MAX_COUNTED_REPORTERS = 12, 5
SEVERITY_POINTS = 20
RECENT_30_POINTS, RECENT_90_POINTS = 10, 5
VOLUME_POINTS, VOLUME_THRESHOLD = 10, 5

TYPE_NAMES = {
    PhoneNumberType.FIXED_LINE: "fixed line", PhoneNumberType.MOBILE: "mobile", PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed line or mobile",
    PhoneNumberType.TOLL_FREE: "toll free", PhoneNumberType.PREMIUM_RATE: "premium rate", PhoneNumberType.SHARED_COST: "shared cost",
    PhoneNumberType.VOIP: "VoIP", PhoneNumberType.PERSONAL_NUMBER: "personal number", PhoneNumberType.PAGER: "pager",
    PhoneNumberType.UAN: "universal access number", PhoneNumberType.VOICEMAIL: "voicemail",
}


class PhoneError(ValueError):
    """A problem with the number the user typed. The message is safe to show to the user."""


@dataclass(frozen=True)
class Normalized:
    e164: str
    region: str | None
    country_code: int
    national: str
    number_type: str
    display: str  # privacy-conscious: everything except the last three digits is masked


def regions() -> list[tuple[str, int]]:
    return sorted((r, phonenumbers.country_code_for_region(r)) for r in phonenumbers.SUPPORTED_REGIONS)


def mask(country_code: int, national: str) -> str:
    return f"+{country_code} " + "X" * max(0, len(national) - 3) + national[-3:]


def display_from_e164(e164: str) -> str:
    try:
        n = phonenumbers.parse(e164, None)
        return mask(n.country_code, str(n.national_number))
    except NumberParseException:
        return "+" + "X" * max(0, len(e164) - 4) + e164[-3:]


def normalize(raw: str | None, region: str | None = None) -> Normalized:
    text = (raw or "").strip()
    if not text:
        raise PhoneError("Enter a phone number.")
    if len(text) > 32 or not re.fullmatch(r"[0-9+()\-.\s]+", text):
        raise PhoneError("A phone number can contain only digits, spaces and the characters + ( ) - .")
    reg = region.strip().upper() if region else None
    if reg and reg not in phonenumbers.SUPPORTED_REGIONS:
        raise PhoneError("Unknown country selection.")
    international = text.startswith("+")
    if not international and not reg:
        raise PhoneError("Choose a country, or start the number with + and its country code.")
    try:
        num = phonenumbers.parse(text, None if international else reg)
    except NumberParseException:
        raise PhoneError("This does not look like a phone number. Check the country code." if international else "This does not look like a phone number.")
    if not phonenumbers.is_valid_number(num):
        raise PhoneError("This is not a valid phone number. Check the country code and the digits." if international
                         else "This is not a valid phone number for the selected country. Check the digits or the country.")
    national = str(num.national_number)
    return Normalized(e164=phonenumbers.format_number(num, PhoneNumberFormat.E164), region=phonenumbers.region_code_for_number(num),
                      country_code=num.country_code, national=national,
                      number_type=TYPE_NAMES.get(phonenumbers.number_type(num), "unknown"), display=mask(num.country_code, national))


@dataclass
class Evidence:
    total: int = 0
    reporters: int = 0
    categories: Counter = field(default_factory=Counter)
    last_report: datetime | None = None
    within_30: int = 0
    within_90: int = 0


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def evidence_from_rows(rows, now: datetime) -> Evidence:
    """rows: (category, reported_by, created_at). Distinct reporters are counted once however many reports they filed."""
    ev = Evidence(total=len(rows))
    known = {r for _, r, _ in rows if r is not None}
    ev.reporters = len(known)  # count only distinct identifiable reporters
    for category, _, created in rows:
        ev.categories[category] += 1
        created = _utc(created)
        if ev.last_report is None or created > ev.last_report:
            ev.last_report = created
        if created >= now - timedelta(days=30):
            ev.within_30 += 1
        if created >= now - timedelta(days=90):
            ev.within_90 += 1
    return ev


@dataclass
class Assessment:
    classification: str
    label: str            # stored on the scan; reuses Sentinel's existing vocabulary (Unknown / Suspicious / Spam / Scam)
    scored: bool
    score: float
    level: str
    evidence_level: str
    indicators: list = field(default_factory=list)   # (name, severity, weight)
    breakdown: list = field(default_factory=list)    # {"rule", "points"}
    explanation: str = ""
    recommendation: str = ""


def level_of(score: float) -> str:
    return "CRITICAL" if score > 80 else "HIGH" if score > 60 else "MEDIUM" if score > 30 else "LOW"


def _sev(weight: float) -> str:
    return "high" if weight > 0.66 else "medium" if weight > 0.33 else "low"


RECOMMENDATIONS = {
    "none": "Treat unexpected calls with normal caution. Never share OTPs, PINs or passwords, and do not call back numbers that came from unexpected messages. If this number contacts you again, report it.",
    "suspicious": "Be careful. Do not share OTPs, bank details or personal information. Hang up and contact the organisation through a number from its official website or your bank card.",
    "high": "Do not answer or call back this number. Never share OTPs, PINs or card details. Block it, and if you already shared information, contact your bank or provider immediately.",
}


def assess(ev: Evidence, now: datetime) -> Assessment:
    if ev.total == 0:
        return Assessment(
            classification="No known threat", label="Unknown", scored=False, score=0.0, level="LOW", evidence_level="none",
            explanation=("The number has a valid format, but Sentinel has no community reports about it. That does not mean it is safe: "
                         "it only means nothing is known. Sentinel used its own community reports and the number's format; no external "
                         "phone threat-intelligence service is configured, so no risk score is given."),
            recommendation=RECOMMENDATIONS["none"])
    breakdown = []
    counted = min(ev.reporters, MAX_COUNTED_REPORTERS)
    breakdown.append({"rule": f"{counted} distinct reporter(s) x {POINTS_PER_REPORTER} points (at most {MAX_COUNTED_REPORTERS} counted)", "points": counted * POINTS_PER_REPORTER})
    severe = [c for c in ev.categories if c in HIGH_SEVERITY]
    if severe:
        breakdown.append({"rule": "At least one report in a high-severity category (" + ", ".join(sorted(severe)) + ")", "points": SEVERITY_POINTS})
    if ev.within_30:
        breakdown.append({"rule": "A report in the last 30 days", "points": RECENT_30_POINTS})
    elif ev.within_90:
        breakdown.append({"rule": "A report in the last 90 days", "points": RECENT_90_POINTS})
    if ev.total >= VOLUME_THRESHOLD:
        breakdown.append({"rule": f"{VOLUME_THRESHOLD} or more reports in total", "points": VOLUME_POINTS})
    score = float(min(sum(b["points"] for b in breakdown), 100))
    level = level_of(score)
    high = level in ("HIGH", "CRITICAL")
    classification = "High risk" if high else "Suspicious"
    label = ("Scam" if severe else "Spam") if high else "Suspicious"
    weight = min(1.0, ev.reporters / MAX_COUNTED_REPORTERS)
    indicators = [(f"Reported by {ev.reporters} different {'user' if ev.reporters == 1 else 'users'}", _sev(weight), round(weight, 3))]
    for category, count in ev.categories.most_common():
        w = min(1.0, count / 5)
        indicators.append((f"{category}: {count} {'report' if count == 1 else 'reports'}", "high" if category in HIGH_SEVERITY else "low", round(max(w, 0.2), 3)))
    days = max(0, (now - ev.last_report).days) if ev.last_report else None
    if days is not None:
        indicators.append((f"Most recent report {days} day(s) ago", "medium" if days <= 30 else "low", 0.5 if days <= 30 else 0.2))
    explanation = (f"{classification}: {ev.reporters} different {'user' if ev.reporters == 1 else 'users'} reported this number ({ev.total} "
                   f"{'report' if ev.total == 1 else 'reports'}). The score of {score:.0f}/100 comes only from these rules: "
                   + "; ".join(f"{b['rule']} = {b['points']}" for b in breakdown)
                   + ". Reports come from Sentinel users and are not independently verified; no external threat-intelligence service was used.")
    return Assessment(classification, label, True, score, level, "substantial" if ev.reporters >= 3 else "moderate" if ev.reporters == 2 else "limited",
                      indicators, breakdown, explanation, RECOMMENDATIONS["high" if high else "suspicious"])
