import json
from pathlib import Path
import joblib
import numpy as np
from ..config import settings

_cache: dict = {}


class ModelUnavailable(Exception):
    pass


def load_url_model():
    """Loads the trained model once and reloads only if the files on disk change."""
    d = Path(settings.model_dir)
    model_path, meta_path = d / "url_phishing_model.joblib", d / "url_phishing_meta.json"
    if not model_path.exists() or not meta_path.exists():
        raise ModelUnavailable()
    stamp = (model_path.stat().st_mtime, meta_path.stat().st_mtime)
    if _cache.get("stamp") != stamp:
        _cache.update(stamp=stamp, model=joblib.load(model_path), meta=json.loads(meta_path.read_text()))
    return _cache["model"], _cache["meta"]


def predict_url(bundle, feats: dict[str, float]):
    """Returns (phishing probability, contributions). A contribution is the drop in phishing probability when one
    feature is replaced by its median value among legitimate training URLs (single-feature substitution)."""
    model, meta = bundle
    names, base = meta["feature_names"], meta["baseline"]
    x = np.array([[feats[n] for n in names]], dtype=float)
    X = np.tile(x, (len(names) + 1, 1))
    for i, n in enumerate(names):
        X[i + 1, i] = base[n]
    probs = model.predict_proba(X)[:, list(model.classes_).index(1)]
    contribs = sorted(((n, float(probs[0] - probs[i + 1])) for i, n in enumerate(names)), key=lambda t: -abs(t[1]))
    return float(probs[0]), contribs
