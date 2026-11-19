"""Loads trained models once and produces predictions plus per-prediction explanations."""
from pathlib import Path
import joblib
import numpy as np
from ..config import settings
from .features import LABELS, URL_FEATURES, clean_text, url_features

_cache: dict[str, dict] = {}


def bundle(name: str) -> dict | None:
    if name not in _cache:
        path = Path(settings.model_dir) / f"{name}.joblib"
        if not path.exists():
            return None
        _cache[name] = joblib.load(path)
    return _cache[name]


def predict_url(url: str):
    """Returns (p_phishing, contributions). Contribution = probability change when that feature is replaced by the
    training-set median (occlusion), so positive values mean the feature pushed the score up."""
    b = bundle("url_phishing_model")
    if b is None:
        return None
    model, meta = b["model"], b["meta"]
    feats = url_features(url)
    x = np.array([[feats[n] for n in URL_FEATURES]], dtype=float)
    idx = list(model.classes_).index(1)
    p = float(model.predict_proba(x)[0, idx])
    X = np.repeat(x, len(URL_FEATURES), axis=0)
    for i, med in enumerate(meta["medians"]):
        X[i, i] = med
    deltas = p - model.predict_proba(X)[:, idx]
    out = [(f"{LABELS[n]}: {feats[n]:g}", float(d)) for n, d in zip(URL_FEATURES, deltas) if abs(d) >= 0.005]
    return p, sorted(out, key=lambda t: -abs(t[1]))


def predict_text(model_name: str, text: str):
    """Returns (p_spam, contributions) where contribution = tf-idf weight x logistic coefficient for each term."""
    b = bundle(model_name)
    if b is None:
        return None
    pipe = b["model"]
    vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
    X = vec.transform([clean_text(text)])
    p = float(clf.predict_proba(X)[0, list(clf.classes_).index(1)])
    terms = vec.get_feature_names_out()
    row = X.tocoo()
    contrib = [(str(terms[j]), float(v * clf.coef_[0][j])) for j, v in zip(row.col, row.data)]
    return p, sorted(contrib, key=lambda t: -abs(t[1]))
