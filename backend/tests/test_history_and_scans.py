import uuid
from app import models
from app.ml import service


def test_history_is_scoped_to_the_user(client, make_user, add_scan):
    ha, a = make_user("a@example.com"); hb, b = make_user("b@example.com")
    sa = add_scan(a, summary="A-only"); sb = add_scan(b, summary="B-only")
    items = client.get("/api/history", headers=ha).json()
    assert items["total"] == 1 and items["items"][0]["input_summary"] == "A-only"
    assert client.get(f"/api/history/{sa}", headers=ha).status_code == 200
    assert client.get(f"/api/history/{sb}", headers=ha).status_code == 404       # someone else's scan


def test_csv_export_contains_only_own_rows(client, make_user, add_scan):
    ha, a = make_user("a@example.com"); hb, b = make_user("b@example.com")
    add_scan(a, summary="mine"); add_scan(b, summary="theirs")
    csv_text = client.get("/api/history/export/csv", headers=ha).content.decode("utf-8-sig")
    assert "mine" in csv_text and "theirs" not in csv_text


def test_csv_export_neutralises_formula_injection(client, make_user, add_scan):
    ha, a = make_user("a@example.com")
    add_scan(a, summary="=HYPERLINK(\"http://x\")")
    assert "'=HYPERLINK" in client.get("/api/history/export/csv", headers=ha).content.decode("utf-8-sig")


def test_website_scan_is_persisted_for_the_caller(client, make_user, db, monkeypatch):
    """The prediction function is replaced by a stub, so this test checks saving and ownership, NOT model accuracy."""
    monkeypatch.setattr(service, "predict_url", lambda url: (0.9, [("URL length: 60", 0.2), ("HTTPS used: 1", -0.1)]))
    monkeypatch.setattr(service, "bundle", lambda name: {"meta": {"version": "test"}})
    ha, a = make_user("a@example.com"); hb, _ = make_user("b@example.com")
    r = client.post("/api/scan/website", json={"url": "http://example.test/login"}, headers=ha)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["label"] == "Phishing" and body["risk_score"] == 90.0 and body["risk_level"] == "CRITICAL"
    scan = db.get(models.Scan, uuid.UUID(body["id"]))
    assert str(scan.user_id) == a and scan.scan_type == "website"
    assert db.query(models.WebsiteScan).count() == 1 and db.query(models.ModelPrediction).count() == 1
    assert db.query(models.Notification).filter_by(user_id=scan.user_id).count() == 1      # CRITICAL risk raises a notification
    assert client.get(f"/api/history/{body['id']}", headers=hb).status_code == 404


def test_scan_without_trained_model_is_a_clear_error(client, make_user):
    ha, _ = make_user("a@example.com")
    r = client.post("/api/scan/website", json={"url": "https://example.com"}, headers=ha)
    assert r.status_code == 503 and "not been trained" in r.json()["detail"]
