"""The metric values in these tests are written by the tests themselves into a temp folder, only to check that the API
returns exactly what a metrics file contains and handles missing or broken files. They are not real model results."""
import json
from pathlib import Path
import joblib
import pytest
from sklearn.linear_model import LogisticRegression
from app.config import settings

METRICS = {"accuracy": 0.91, "precision": 0.8, "recall": 0.7, "f1": 0.75, "roc_auc": 0.88,
           "confusion_matrix": [[10, 2], [3, 15]], "test_size": 30,
           "meta": {"description": "test model", "version": "7", "trained_at": "2026-01-01T00:00:00+00:00", "seed": 42,
                    "features": ["a", "b", "c"], "medians": [1, 2, 3], "positive_class": "spam"}}


@pytest.fixture
def model_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "model_dir", str(tmp_path))
    return tmp_path


def by_key(client, headers):
    r = client.get("/api/models/performance", headers=headers)
    assert r.status_code == 200
    return {m["key"]: m for m in r.json()["models"]}


def put_model(folder: Path, key):
    joblib.dump({"model": LogisticRegression(), "meta": {}}, folder / f"{key}.joblib")


def test_all_not_trained_when_folder_empty(client, make_user, model_dir):
    h, _ = make_user("a@example.com")
    m = by_key(client, h)
    assert set(m) == {"url_phishing_model", "email_model", "sms_model"}
    assert all(x["status"] == "not_trained" and all(v is None for v in x["metrics"].values()) for x in m.values())


def test_trained_model_returns_exact_file_values(client, make_user, model_dir):
    h, _ = make_user("a@example.com")
    put_model(model_dir, "email_model")
    (model_dir / "email_model_metrics.json").write_text(json.dumps(METRICS))
    e = by_key(client, h)["email_model"]
    assert e["status"] == "trained" and e["algorithm"] == "LogisticRegression"
    assert e["metrics"] == {k: METRICS[k] for k in ("accuracy", "precision", "recall", "f1", "roc_auc")}
    assert e["confusion_matrix"] == [[10, 2], [3, 15]] and e["test_size"] == 30
    assert e["feature_count"] == 3 and e["version"] == "7" and e["positive_class"] == "spam"
    assert e["dataset"] is None and e["train_size"] is None and e["class_names"] is None   # not in the file -> reported missing
    assert "medians" not in json.dumps(e)


def test_model_without_metrics_file_and_broken_metrics(client, make_user, model_dir):
    h, _ = make_user("a@example.com")
    put_model(model_dir, "sms_model")
    assert by_key(client, h)["sms_model"]["status"] == "metrics_unavailable"
    (model_dir / "sms_model_metrics.json").write_text("{not json")
    assert by_key(client, h)["sms_model"]["status"] == "metrics_unavailable"
    put_model(model_dir, "url_phishing_model")
    (model_dir / "url_phishing_model_metrics.json").write_text(json.dumps({"accuracy": 5, "confusion_matrix": [[1, 2, 3]], "f1": "x"}))
    u = by_key(client, h)["url_phishing_model"]
    assert u["status"] == "trained" and u["metrics"]["accuracy"] is None and u["metrics"]["f1"] is None and u["confusion_matrix"] is None


def test_no_request_parameter_can_select_a_file(client, make_user, model_dir):
    h, _ = make_user("a@example.com")
    r = client.get("/api/models/performance?name=../../etc/passwd&path=/etc/passwd", headers=h)
    assert r.status_code == 200 and len(r.json()["models"]) == 3
