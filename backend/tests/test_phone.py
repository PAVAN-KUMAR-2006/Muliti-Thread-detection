"""Phase 9E tests. Numbers used are ordinary valid-format numbers; no real person is contacted (nothing is ever dialled)."""
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from app import models, phone_service as ps
from app.routes_auth import limiter

IN, US, UK = "+919876543210", "+16502530000", "+442079460958"
DESC = "Caller said my account was blocked and asked me for the OTP."


def scan(client, h, number, region=None):
    return client.post("/api/phone/scan", json={"number": number, **({"region": region} if region else {})}, headers=h)


def report(client, h, number=IN, category="Financial Scam", description=DESC, **extra):
    return client.post("/api/phone/reports", json={"number": number, "category": category, "description": description, **extra}, headers=h)


def users(make_user, n):
    return [make_user(f"user{i}@example.com")[0] for i in range(n)]


# ---------- number validation and normalisation ----------
@pytest.mark.parametrize("raw,region,e164", [("98765 43210", "IN", IN), ("+91 98765 43210", None, IN), ("+1 650 253 0000", None, US),
                                             ("020 7946 0958", "GB", UK), ("(650) 253-0000", "US", US)])
def test_valid_numbers_are_normalised(raw, region, e164):
    assert ps.normalize(raw, region).e164 == e164


@pytest.mark.parametrize("raw,region", [("", "IN"), ("   ", "IN"), ("12345", "IN"), ("9876543210", "US"), ("+999123456", None), ("98765 43210", None),
                                        ("call me", "IN"), ("+" + "9" * 40, None), ("98765 43210", "ZZ")])
def test_invalid_numbers_are_rejected(raw, region):
    with pytest.raises(ps.PhoneError):
        ps.normalize(raw, region)


def test_display_masks_all_but_the_last_three_digits():
    assert ps.normalize(IN).display == "+91 XXXXXXX210"


def test_international_numbers_are_not_rejected_for_being_non_indian(client, make_user):
    h = users(make_user, 1)[0]
    for n in (US, UK):
        assert scan(client, h, n).status_code == 200


# ---------- scan results ----------
def test_unknown_number_is_not_scored_and_not_called_safe(client, make_user, db):
    h = users(make_user, 1)[0]
    r = scan(client, h, IN, "IN")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["label"] == "Unknown" and d["classification"] == "No known threat"
    assert d["risk_score"] is None and d["risk_level"] is None and d["details"]["scored"] is False
    assert d["details"]["format_valid"] is True and d["details"]["external_intel"] is False
    assert "does not mean it is safe" in d["explanation"] and d["details"]["evidence"]["reports"] == 0
    assert db.query(models.PhoneScan).count() == 1


@pytest.mark.parametrize("bad", ["", "12345", "+999123456"])
def test_invalid_input_is_a_clear_422_and_saves_nothing(client, make_user, db, bad):
    h = users(make_user, 1)[0]
    assert scan(client, h, bad, "IN").status_code == 422
    assert db.query(models.Scan).count() == 0


def test_a_single_report_makes_the_number_suspicious_not_high_risk(client, make_user):
    ha, hb = users(make_user, 2)
    assert report(client, ha).status_code == 201
    d = scan(client, hb, IN).json()
    assert d["classification"] == "Suspicious" and d["label"] == "Suspicious" and d["details"]["scored"] is True
    assert d["details"]["evidence"]["reporters"] == 1 and d["details"]["evidence_level"] == "limited"
    assert sum(b["points"] for b in d["details"]["score_breakdown"]) == d["risk_score"]


def test_several_independent_reports_make_it_high_risk_and_notify(client, make_user, db):
    hs = users(make_user, 4)
    for h in hs[:3]:
        assert report(client, h).status_code == 201
    d = scan(client, hs[3], IN).json()
    assert d["classification"] == "High risk" and d["label"] == "Scam" and d["risk_level"] in ("HIGH", "CRITICAL")
    assert d["details"]["evidence_level"] == "substantial" and d["details"]["evidence"]["categories"] == {"Financial Scam": 3}
    assert any("3 different users" in i["name"] for i in d["indicators"])
    assert db.query(models.Notification).filter_by(title="High-risk phone number").count() == 1
    assert db.query(models.ThreatIndicator).count() == len(d["indicators"])


def test_many_reports_from_one_user_do_not_inflate_the_reporter_count(client, make_user):
    h = users(make_user, 1)[0]
    for cat in ("Spam Call", "Robocall", "Telemarketing", "Other", "Financial Scam"):
        assert report(client, h, category=cat).status_code == 201
    ev = scan(client, h, IN).json()["details"]["evidence"]
    assert ev["reports"] == 5 and ev["reporters"] == 1


def test_old_reports_score_lower_than_recent_ones(db):
    now = datetime.now(timezone.utc)
    recent = ps.assess(ps.evidence_from_rows([("Spam Call", uuid.uuid4(), now - timedelta(days=2))], now), now)
    old = ps.assess(ps.evidence_from_rows([("Spam Call", uuid.uuid4(), now - timedelta(days=400))], now), now)
    assert recent.score > old.score


# ---------- reports: validation, duplicates, privacy ----------
def test_report_validation(client, make_user):
    h = users(make_user, 1)[0]
    assert report(client, h, description="short").status_code == 422
    assert report(client, h, description="   ").status_code == 422
    assert report(client, h, category="Made Up").status_code == 422
    assert report(client, h, number="12345").status_code == 422
    assert client.post("/api/phone/reports", json={"number": IN}, headers=h).status_code == 422


def test_duplicate_report_is_rejected_but_another_category_is_allowed(client, make_user):
    h = users(make_user, 1)[0]
    assert report(client, h).status_code == 201
    r = report(client, h)
    assert r.status_code == 409 and "already reported" in r.json()["detail"]
    assert report(client, h, category="Robocall").status_code == 201


def test_description_is_sanitised(client, make_user):
    h = users(make_user, 1)[0]
    r = report(client, h, description="<script>alert(1)</script>Caller pretended to be my bank\x00 and asked for money.", evidence="<b>ref</b> 12345")
    assert r.status_code == 201
    body = r.json()
    assert "<" not in body["description"] and "\x00" not in body["description"] and body["description"].startswith("alert(1)")
    assert body["evidence"] == "ref 12345"


def test_report_responses_never_expose_the_reporter_or_the_full_number(client, make_user):
    h = users(make_user, 1)[0]
    r = report(client, h)
    text = r.text
    for secret in ("reported_by", "user_id", "user0@example.com", IN, IN[1:]):
        assert secret not in text
    assert r.json()["number_display"] == "+91 XXXXXXX210"


def test_scan_results_do_not_leak_other_users_descriptions(client, make_user):
    ha, hb = users(make_user, 2)
    report(client, ha, description="PRIVATE-DETAIL about what the caller said to me.")
    assert "PRIVATE-DETAIL" not in scan(client, hb, IN).text


# ---------- authentication and per-user access ----------
@pytest.mark.parametrize("method,path,body", [("post", "/api/phone/scan", {"number": IN}), ("post", "/api/phone/reports", {"number": IN, "category": "Other", "description": DESC}),
                                              ("get", "/api/phone/reports", None), ("get", "/api/phone/regions", None),
                                              ("get", f"/api/phone/reports/{uuid.uuid4()}", None), ("get", f"/api/phone/scans/{uuid.uuid4()}", None)])
def test_every_phone_endpoint_requires_authentication(client, method, path, body):
    r = getattr(client, method)(path, **({"json": body} if body else {}))
    assert r.status_code == 401


def test_users_only_see_their_own_reports(client, make_user):
    ha, hb = users(make_user, 2)
    rid = report(client, ha).json()["id"]
    report(client, hb, category="Robocall")
    assert [x["category"] for x in client.get("/api/phone/reports", headers=ha).json()] == ["Financial Scam"]
    assert client.get(f"/api/phone/reports/{rid}", headers=ha).status_code == 200
    assert client.get(f"/api/phone/reports/{rid}", headers=hb).status_code == 404


def test_phone_scans_are_private_to_their_owner(client, make_user):
    ha, hb = users(make_user, 2)
    sid = scan(client, ha, IN).json()["id"]
    assert client.get(f"/api/phone/scans/{sid}", headers=ha).json()["normalized"] == IN
    assert client.get(f"/api/phone/scans/{sid}", headers=hb).status_code == 404
    assert client.get(f"/api/history/{sid}", headers=hb).status_code == 404
    assert client.get("/api/history?type=phone", headers=hb).json()["total"] == 0


def test_regions_endpoint_lists_countries_with_dial_codes(client, make_user):
    h = users(make_user, 1)[0]
    regions = {r["region"]: r["dial_code"] for r in client.get("/api/phone/regions", headers=h).json()}
    assert regions["IN"] == "+91" and regions["US"] == "+1" and len(regions) > 200


# ---------- rate limiting ----------
@pytest.fixture
def limiter_on():
    limiter.reset(); limiter.enabled = True
    yield
    limiter.enabled = False; limiter.reset()


def test_report_endpoint_is_rate_limited(client, make_user, limiter_on):
    h = users(make_user, 1)[0]
    codes = [report(client, h, number=f"+9198765{43000 + i}").status_code for i in range(12)]
    assert codes[:10] == [201] * 10 and 429 in codes[10:]


def test_daily_report_cap(client, make_user, db):
    h, uid = make_user("cap@example.com")
    for i in range(20):
        db.add(models.PhoneReport(number=f"+9198765{44000 + i}", category="Other", description=DESC, reported_by=uuid.UUID(uid)))
    db.commit()
    r = report(client, h, number="+919876545999")
    assert r.status_code == 429 and "daily limit" in r.json()["detail"]


# ---------- integration with history, dashboard, analytics and exports ----------
def test_phone_scans_flow_into_history_dashboard_analytics_and_exports(client, make_user):
    hs = users(make_user, 4)
    for h in hs[:3]:
        report(client, h)
    sid = scan(client, hs[3], IN).json()["id"]
    h = hs[3]
    hist = client.get("/api/history?type=phone", headers=h).json()
    assert hist["total"] == 1 and hist["items"][0]["input_summary"] == "+91 XXXXXXX210"
    detail = client.get(f"/api/history/{sid}", headers=h).json()
    assert detail["scan_type"] == "phone" and detail["indicators"] and "High risk" in detail["explanation"]
    assert {i["name"] for i in client.get("/api/analytics/scanner-usage", headers=h).json()["items"]} >= {"phone"}
    assert {i["name"]: i["count"] for i in client.get("/api/analytics/scanner-usage", headers=h).json()["items"]}["phone"] == 1
    assert client.get("/api/dashboard/overview", headers=h).json()["by_type"]["phone"] == 1
    alerts = client.get("/api/analytics/high-risk", headers=h).json()
    assert alerts["total"] == 1 and alerts["items"][0]["scan_type"] == "phone"
    csv_text = client.get("/api/history/export/csv", headers=h).content.decode("utf-8-sig")
    assert "+91 XXXXXXX210" in csv_text and IN not in csv_text


# ---------- database migration ----------
def test_migration_0003_upgrades_a_0002_database_and_keeps_existing_rows(db):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text
    from app.database import engine
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini")); cfg.set_main_option("script_location", str(root / "alembic"))
    db.close()
    with engine.begin() as c:   # recreate the table exactly as it was before Phase 9E, with one existing row
        c.execute(text("DROP TABLE phone_scans")); c.execute(text("DROP TABLE phone_reports"))
        c.execute(text("CREATE TABLE phone_reports (id CHAR(32) NOT NULL PRIMARY KEY, number VARCHAR(32) NOT NULL, category VARCHAR(48) NOT NULL, reported_by CHAR(32), created_at DATETIME)"))
        c.execute(text("CREATE INDEX ix_phone_reports_number ON phone_reports (number)"))
        c.execute(text("INSERT INTO phone_reports (id, number, category, reported_by, created_at) VALUES ('0123456789abcdef0123456789abcdef', '+919876543210', 'Spam Call', NULL, '2026-01-01 00:00:00')"))
        c.execute(text("DROP TABLE IF EXISTS alembic_version"))
    command.stamp(cfg, "0002")
    command.upgrade(cfg, "head")
    insp = inspect(engine)
    assert {"description", "evidence", "region"} <= {c["name"] for c in insp.get_columns("phone_reports")}
    assert "phone_scans" in insp.get_table_names()
    assert "uq_phone_report_user_number_category" in {u["name"] for u in insp.get_unique_constraints("phone_reports")}
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM phone_reports")).scalar() == 1
        assert c.execute(text("SELECT category FROM phone_reports")).scalar() == "Spam Call"
        assert c.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0003"
    command.upgrade(cfg, "head")   # running it again is a no-op


def test_single_alembic_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini")); cfg.set_main_option("script_location", str(root / "alembic"))
    assert ScriptDirectory.from_config(cfg).get_heads() == ["0003"]
