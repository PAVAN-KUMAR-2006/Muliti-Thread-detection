"""Phase 9D backend tests: the dashboard's data sources. Rows are inserted straight into the throwaway test database."""
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from app import models


@pytest.fixture
def put(db):
    def make(user_id, scan_type="website", label="Phishing", score=90.0, level="CRITICAL", status="completed", days_ago=0, summary="x", explanation="why"):
        s = models.Scan(user_id=uuid.UUID(user_id), scan_type=scan_type, input_summary=summary, label=label, risk_score=score, risk_level=level,
                        confidence=0.9, status=status, explanation=explanation, recommendation="r",
                        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago, minutes=1))
        db.add(s); db.commit()
        return str(s.id)
    return make


# ---------- high-risk alerts ----------
def test_high_risk_returns_only_high_and_critical_newest_first_with_status(client, make_user, put):
    h, u = make_user("a@example.com")
    put(u, level="LOW", label="Safe", score=5, summary="low")
    put(u, level="MEDIUM", label="Suspicious", score=45, summary="medium")
    put(u, level="HIGH", label="Spam", score=70, summary="high-older", days_ago=2, status="completed")
    put(u, level="CRITICAL", label="Phishing", score=95, summary="critical-newest", days_ago=0)
    r = client.get("/api/analytics/high-risk", headers=h).json()
    assert r["total"] == 2
    assert [i["risk_level"] for i in r["items"]] == ["CRITICAL", "HIGH"]
    assert all(i["status"] == "completed" and "id" in i and i["scan_type"] == "website" for i in r["items"])


def test_high_risk_limit_and_total_and_validation(client, make_user, put):
    h, u = make_user("a@example.com")
    for n in range(6): put(u, summary=f"s{n}", days_ago=0)
    r = client.get("/api/analytics/high-risk?limit=2", headers=h).json()
    assert len(r["items"]) == 2 and r["total"] == 6          # total counts every alert in the window, not only the page
    assert client.get("/api/analytics/high-risk?limit=0", headers=h).status_code == 422
    assert client.get("/api/analytics/high-risk?limit=21", headers=h).status_code == 422


def test_high_risk_respects_the_time_window_and_scanner_filter(client, make_user, put):
    h, u = make_user("a@example.com")
    put(u, summary="recent", days_ago=1); put(u, summary="old", days_ago=40); put(u, scan_type="email", summary="mail", days_ago=1)
    assert client.get("/api/analytics/high-risk?days=7", headers=h).json()["total"] == 2
    assert client.get("/api/analytics/high-risk?days=90", headers=h).json()["total"] == 3
    only = client.get("/api/analytics/high-risk?days=7&scanner=email", headers=h).json()
    assert only["total"] == 1 and only["items"][0]["scan_type"] == "email"


def test_high_risk_is_user_scoped_and_requires_auth(client, make_user, put):
    ha, a = make_user("a@example.com"); hb, b = make_user("b@example.com")
    put(a, summary="A-alert"); put(b, summary="B-alert")
    ra = client.get("/api/analytics/high-risk", headers=ha).json()
    assert ra["total"] == 1 and "B-alert" not in str(ra)
    assert client.get("/api/analytics/high-risk").status_code == 401


def test_high_risk_empty_for_a_new_user(client, make_user):
    h, _ = make_user("new@example.com")
    assert client.get("/api/analytics/high-risk", headers=h).json() == {"total": 0, "items": []}


# ---------- scan status ----------
def test_scan_status_groups_by_status_and_reports_only_what_exists(client, make_user, put):
    h, u = make_user("a@example.com")
    put(u, status="completed"); put(u, status="completed"); put(u, status="failed", level="LOW", label="Safe", score=0)
    r = client.get("/api/analytics/scan-status", headers=h).json()
    assert r["total"] == 3 and r["items"] == [{"status": "completed", "count": 2}, {"status": "failed", "count": 1}]
    assert client.get("/api/analytics/scan-status?days=7&scanner=email", headers=h).json() == {"items": [], "total": 0}


def test_scan_status_window_isolation_and_auth(client, make_user, put):
    ha, a = make_user("a@example.com"); hb, b = make_user("b@example.com")
    put(a, days_ago=1); put(a, days_ago=40); put(b, days_ago=1)
    assert client.get("/api/analytics/scan-status?days=7", headers=ha).json()["total"] == 1
    assert client.get("/api/analytics/scan-status?days=90", headers=ha).json()["total"] == 2
    assert client.get("/api/analytics/scan-status").status_code == 401


# ---------- counts used by the scanner-activity panel ----------
def test_usage_distribution_and_history_agree_and_nothing_is_double_counted(client, make_user, put, db):
    h, u = make_user("a@example.com")
    sid = put(u, scan_type="website", label="Phishing", level="CRITICAL")
    put(u, scan_type="email", label="Safe", level="LOW", score=3); put(u, scan_type="email", label="Spam", level="HIGH", score=70)
    # a scan with several indicators and predictions must still count once
    sc = uuid.UUID(sid)
    for n in range(3): db.add(models.ThreatIndicator(scan_id=sc, name=f"i{n}", severity="high", weight=0.5))
    for n in range(2): db.add(models.ModelPrediction(scan_id=sc, model_name="m", model_version="1", probability=0.9))
    db.commit()
    usage = {i["name"]: i["count"] for i in client.get("/api/analytics/scanner-usage", headers=h).json()["items"]}
    assert usage["website"] == 1 and usage["email"] == 2 and usage["message"] == 0 and usage["qr"] == 0 and usage["file"] == 0
    labels = {i["name"]: i["count"] for i in client.get("/api/analytics/threat-distribution", headers=h).json()["items"]}
    assert labels["Phishing"] == 1 and labels["Safe"] == 1 and labels["Spam"] == 1 and labels["Scam"] == 0
    assert client.get("/api/analytics/scanner-usage", headers=h).json()["total"] == client.get("/api/history", headers=h).json()["total"] == 3


# ---------- dashboard overview ----------
def test_overview_for_a_user_with_no_scans(client, make_user):
    h, _ = make_user("new@example.com")
    r = client.get("/api/dashboard/overview", headers=h).json()
    assert r["total"] == 0 and r["state"] == "No data" and r["recent"] == [] and r["last_scan"] is None
    assert sum(r["by_type"].values()) == 0 and len(r["activity"]) == 30 and all(p["count"] == 0 for p in r["activity"])


def test_overview_counts_only_the_users_own_scans(client, make_user, put):
    ha, a = make_user("a@example.com"); hb, b = make_user("b@example.com")
    put(a, scan_type="website"); put(a, scan_type="qr", label="Safe", level="LOW", score=1)
    for _ in range(4): put(b, scan_type="file")
    r = client.get("/api/dashboard/overview", headers=ha).json()
    assert r["total"] == 2 and r["by_type"]["website"] == 1 and r["by_type"]["qr"] == 1 and r["by_type"]["file"] == 0
    assert r["state"] == "Elevated" and r["high_risk"] == 1


# ---------- regression: the 7/30/90 day filters must be accepted as plain numbers in the query string ----------
@pytest.mark.parametrize("path", ["/api/dashboard/overview", "/api/analytics/overview", "/api/analytics/scanner-usage", "/api/analytics/threat-distribution",
                                  "/api/analytics/risk-distribution", "/api/analytics/scan-trends", "/api/analytics/threat-trends",
                                  "/api/analytics/high-risk", "/api/analytics/scan-status"])
@pytest.mark.parametrize("days", [7, 30, 90])
def test_days_filter_is_accepted(client, make_user, path, days):
    if "trends" in path:
        pytest.skip("these two endpoints use PostgreSQL date_trunc, which SQLite cannot run; they need a PostgreSQL run")
    h, _ = make_user("a@example.com")
    r = client.get(f"{path}?days={days}", headers=h)
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("path", ["/api/dashboard/overview", "/api/analytics/high-risk", "/api/analytics/scan-status"])
def test_days_filter_rejects_other_values_clearly(client, make_user, path):
    h, _ = make_user("a@example.com")
    for bad in ("14", "0", "abc"):
        assert client.get(f"{path}?days={bad}", headers=h).status_code == 422
