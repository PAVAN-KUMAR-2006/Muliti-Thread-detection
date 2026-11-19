"""Train the URL phishing Random Forest.
Dataset: put ml/datasets/urls.csv (columns: url,label; label 1/phishing/malicious or 0/benign/legitimate).
If absent, the script downloads PhishTank (phishing) + Tranco top-1M (benign). That fallback is biased:
benign entries are bare domains while phishing entries have paths, so a supplied balanced dataset is better.
Run (from repo root): docker compose exec -e PYTHONPATH=/app backend python /ml/training/train_url_model.py"""
import csv
import io
import random
import sys
import zipfile
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent))
from train_utils import DATA, SEED, download, evaluate, save  # noqa: E402
from app.ml.features import URL_FEATURES, url_features  # noqa: E402

BAD = {"1", "phishing", "malicious", "bad", "defacement", "malware"}
GOOD = {"0", "benign", "legitimate", "good"}


def load() -> list[tuple[str, int]]:
    path = DATA / "urls.csv"
    rows: list[tuple[str, int]] = []
    if path.exists():
        for r in csv.DictReader(open(path, encoding="utf-8", errors="ignore")):
            lab = str(r.get("label", r.get("type", ""))).strip().lower()
            if r.get("url") and (lab in BAD or lab in GOOD):
                rows.append((r["url"].strip(), int(lab in BAD)))
        return rows
    print("WARNING: no ml/datasets/urls.csv; using PhishTank + Tranco fallback (see file header about bias).")
    rng = random.Random(SEED)
    pt = download("http://data.phishtank.com/data/online-valid.csv", DATA / "phishtank.csv")
    bad = [r["url"] for r in csv.DictReader(open(pt, encoding="utf-8", errors="ignore")) if r.get("url")]
    tz = zipfile.ZipFile(download("https://tranco-list.eu/top-1m.csv.zip", DATA / "tranco.zip"))
    good = [f"https://{line.split(',')[1]}" for line in io.TextIOWrapper(tz.open(tz.namelist()[0])).read().splitlines()[:50000] if "," in line]
    n = min(20000, len(bad), len(good))
    return [(u, 1) for u in rng.sample(bad, n)] + [(u, 0) for u in rng.sample(good, n)]


def main():
    rows = list(dict.fromkeys(load()))
    rows = [(u, y) for u, y in rows if 4 < len(u) < 2048]
    print(f"{len(rows)} URLs ({sum(y for _, y in rows)} phishing)")
    X = np.array([[url_features(u)[f] for f in URL_FEATURES] for u, _ in rows], dtype=float)
    y = np.array([lab for _, lab in rows])
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    model = RandomForestClassifier(n_estimators=300, min_samples_leaf=2, class_weight="balanced", random_state=SEED, n_jobs=-1)
    model.fit(Xtr, ytr)
    meta = {"features": URL_FEATURES, "medians": np.median(Xtr, axis=0).tolist(), "description": "Random Forest on lexical URL features"}
    save("url_phishing_model", model, meta, evaluate(model, Xte, yte))


if __name__ == "__main__":
    main()
