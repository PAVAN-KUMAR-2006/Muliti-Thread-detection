import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
MODELS, DATA, SEED = ROOT / "models", ROOT / "datasets", 42


def download(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    DATA.mkdir(exist_ok=True)
    print(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Sentinel training script)"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def evaluate(model, X_test, y_test) -> dict:
    pred, proba = model.predict(X_test), model.predict_proba(X_test)[:, 1]
    return {"accuracy": accuracy_score(y_test, pred), "precision": precision_score(y_test, pred),
            "recall": recall_score(y_test, pred), "f1": f1_score(y_test, pred), "roc_auc": roc_auc_score(y_test, proba),
            "confusion_matrix": confusion_matrix(y_test, pred).tolist(), "test_size": len(y_test)}


def save(name: str, model, meta: dict, metrics: dict) -> None:
    MODELS.mkdir(exist_ok=True)
    meta = {**meta, "version": "1", "trained_at": datetime.now(timezone.utc).isoformat(), "seed": SEED}
    joblib.dump({"model": model, "meta": meta}, MODELS / f"{name}.joblib")
    (MODELS / f"{name}_metrics.json").write_text(json.dumps({**metrics, **{"meta": meta}}, indent=2))
    print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in metrics.items()}, indent=2))
    print(f"Saved {MODELS / (name + '.joblib')}")


def train_text(name: str, texts: list[str], labels: list[int], description: str) -> None:
    from app.ml.features import clean_text
    X = [clean_text(t) for t in texts]
    print(f"{len(X)} samples, {sum(labels)} positive (spam)")
    Xtr, Xte, ytr, yte = train_test_split(X, labels, test_size=0.2, stratify=labels, random_state=SEED)
    pipe = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, stop_words="english", max_features=50000)),
                     ("clf", LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000, random_state=SEED))])
    pipe.fit(Xtr, ytr)
    save(name, pipe, {"description": description, "positive_class": "spam"}, evaluate(pipe, Xte, yte))
