"""Model performance. Reads only the *_metrics.json files written by the training scripts, from the configured model
directory. The set of models is a fixed allowlist; no request parameter chooses a file or path. Nothing here is computed
or estimated: a value that is missing from the file is reported as missing."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends
from . import models
from .config import settings
from .deps import get_current_user
from .ml import service

router = APIRouter(prefix="/api/models", tags=["models"])
MODELS = (("url_phishing_model", "URL Phishing Model", "website"), ("email_model", "Email Model", "email"),
          ("sms_model", "Message (SMS) Model", "message"))
METRICS = ("accuracy", "precision", "recall", "f1", "roc_auc")
MAX_BYTES = 1_000_000


def read_json(path: Path):
    try:
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def ratio(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 else None


def matrix(m):
    ok = isinstance(m, list) and len(m) == 2 and all(
        isinstance(r, list) and len(r) == 2 and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in r) for r in m)
    return m if ok else None


def text(v, n=300):
    return v[:n] if isinstance(v, str) and v.strip() else None


def algorithm_of(obj) -> str:
    steps = getattr(obj, "steps", None)  # a scikit-learn Pipeline
    return " + ".join(type(s).__name__ for _, s in steps) if steps else type(obj).__name__


def describe(key: str, title: str, scanner: str) -> dict:
    folder = Path(settings.model_dir)
    out = {"key": key, "name": title, "scanner": scanner, "status": "not_trained", "algorithm": None,
           "metrics": {m: None for m in METRICS}, "confusion_matrix": None, "test_size": None, "train_size": None,
           "feature_count": None, "dataset": None, "description": None, "version": None, "trained_at": None, "seed": None,
           "positive_class": None, "class_names": None, "metrics_file": f"{key}_metrics.json"}
    if not (folder / f"{key}.joblib").is_file():
        return out
    try:
        bundle = service.bundle(key)
        out["algorithm"] = algorithm_of(bundle["model"]) if bundle else None
    except Exception:  # an unreadable model file must not break the whole page
        out["algorithm"] = None
    raw = read_json(folder / f"{key}_metrics.json")
    if raw is None:
        out["status"] = "metrics_unavailable"
        return out
    meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    out["status"] = "trained"
    out["metrics"] = {m: ratio(raw.get(m)) for m in METRICS}
    out["confusion_matrix"] = matrix(raw.get("confusion_matrix"))
    out["test_size"] = raw.get("test_size") if isinstance(raw.get("test_size"), int) else None
    out["train_size"] = raw.get("train_size") if isinstance(raw.get("train_size"), int) else None
    out["feature_count"] = len(meta["features"]) if isinstance(meta.get("features"), list) else None
    out["dataset"] = text(meta.get("dataset"))
    out["description"] = text(meta.get("description"))
    out["version"] = text(meta.get("version"), 40)
    out["trained_at"] = text(meta.get("trained_at"), 40)
    out["seed"] = meta.get("seed") if isinstance(meta.get("seed"), int) else None
    out["positive_class"] = text(meta.get("positive_class"), 40)
    names = meta.get("class_names")
    out["class_names"] = names if isinstance(names, list) and len(names) == 2 and all(isinstance(n, str) for n in names) else None
    return out  # the 'medians' array and any other internals in meta are deliberately not returned


@router.get("/performance")
def performance(user: models.User = Depends(get_current_user)):
    return {"models": [describe(*m) for m in MODELS]}
