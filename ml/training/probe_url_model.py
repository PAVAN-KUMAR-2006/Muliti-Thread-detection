"""READ-ONLY probe of the trained URL model. It loads the model and the cached datasets and prints a report.
It writes nothing: no database access, no model or dataset changes, no scans saved.

It runs each URL through three separate layers so a wrong score can be traced to the layer that caused it:
  1. raw model     joblib model + the 23 features, called directly
  2. service layer app.ml.service.predict_url (what the API calls for the probability and explanation)
  3. API layer     app.routes_scan.url_analysis (what /api/scan/website calls: label thresholds and score)
Run: docker compose exec -e PYTHONPATH=/app backend python /ml/training/probe_url_model.py"""
import csv
import io
import random
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import joblib
import numpy as np
from fastapi import HTTPException

from app.config import settings
from app.ml import service
from app.ml.features import URL_FEATURES, normalize_url, url_features
from app.routes_scan import level_of, url_analysis

PROBE = ["https://google.com", "https://www.google.com", "https://www.google.com/", "https://microsoft.com",
         "https://www.microsoft.com", "https://github.com", "https://www.github.com", "https://amazon.com", "https://www.amazon.com"]
EXTRA = ["https://www.google.com/search?q=test", "https://mail.google.com", "https://wikipedia.org", "https://www.wikipedia.org",
         "http://secure-login.account-verify.example-bank.com.xyz/update?id=1"]  # last one: synthetic, for contrast only
DATA = Path(__file__).resolve().parents[1] / "datasets"
SEED = 42


def probe():
    path = Path(settings.model_dir) / "url_phishing_model.joblib"
    if not path.exists():
        sys.exit(f"Model file not found: {path}")
    b = joblib.load(path)
    model, meta = b["model"], b["meta"]
    idx = list(model.classes_).index(1)
    print("== 1. MODEL")
    print(f"file: {path}\ntype: {type(model).__name__}  trees: {getattr(model, 'n_estimators', 'n/a')}  classes: {list(model.classes_)}")
    print(f"version: {meta.get('version')}  trained_at: {meta.get('trained_at')}  n_features_in_: {model.n_features_in_}")
    print(f"feature order matches current code: {list(meta['features']) == URL_FEATURES}")
    imp = sorted(zip(URL_FEATURES, model.feature_importances_), key=lambda t: -t[1])[:8]
    print("global top feature importances: " + ", ".join(f"{n} {v:.3f}" for n, v in imp))

    urls = PROBE + EXTRA
    rows = []
    for u in urls:
        norm = normalize_url(u)
        f = url_features(norm)
        x = np.array([[f[n] for n in URL_FEATURES]], dtype=float)
        raw_p, raw_cls = float(model.predict_proba(x)[0, idx]), int(model.predict(x)[0])
        svc = service.predict_url(norm)
        try:
            api = url_analysis(u)
            api_p, api_label = api[1], api[2]
        except HTTPException as e:
            api_p, api_label = None, f"error {e.status_code}"
        rows.append((u, f, raw_p, raw_cls, svc, api_p, api_label))

    print("\n== 2. PREDICTIONS (raw model / service layer / API layer)")
    print(f"{'#':>2} {'URL':<62} {'cls':>3} {'p_raw':>7} {'p_svc':>7} {'p_api':>7} {'score':>6} {'label / level':<22} layers agree")
    for i, (u, f, rp, rc, svc, ap, al) in enumerate(rows, 1):
        sp = svc[0] if svc else None
        agree = sp is not None and ap is not None and abs(rp - sp) < 1e-9 and abs(rp - ap) < 1e-9
        score = f"{round(ap * 100, 1):.1f}" if ap is not None else "-"
        lvl = f"{al} / {level_of(round(ap * 100, 1))}" if ap is not None else al
        print(f"{i:>2} {u[:62]:<62} {rc:>3} {rp:7.4f} {(sp if sp is not None else float('nan')):7.4f} {(ap if ap is not None else float('nan')):7.4f} {score:>6} {lvl:<22} {'yes' if agree else 'NO'}")

    print("\n== 3. THE 23 EXTRACTED FEATURES (columns = the numbered URLs above)")
    print(f"{'feature':<22}" + "".join(f"{i:>9}" for i in range(1, len(rows) + 1)))
    for n in URL_FEATURES:
        print(f"{n:<22}" + "".join(f"{r[1][n]:>9.4g}" for r in rows))

    print("\n== 4. TOP CONTRIBUTING FEATURES (change in phishing probability when that feature is set to the training median; + raises risk)")
    for i, (u, f, rp, rc, svc, ap, al) in enumerate(rows, 1):
        top = (svc[1][:5] if svc else [])
        print(f"{i:>2} {u[:70]}\n     " + ("; ".join(f"{n} ({d:+.3f})" for n, d in top) or "none above the 0.005 threshold"))


def training_check():
    print("\n== 5. TRAINING-DATA CHECK (rebuilds the same seed-42 sample from the cached files; reads only)")
    pt, tz = DATA / "phishtank.csv", DATA / "tranco.zip"
    if not (pt.exists() and tz.exists()):
        print(f"skipped: {pt.name} and/or {tz.name} not found in {DATA}")
        return
    bad = [r["url"] for r in csv.DictReader(open(pt, encoding="utf-8", errors="ignore")) if r.get("url")]
    z = zipfile.ZipFile(tz)
    good = [f"https://{line.split(',')[1]}" for line in io.TextIOWrapper(z.open(z.namelist()[0])).read().splitlines()[:50000] if "," in line]
    n = min(20000, len(bad), len(good))
    rng = random.Random(SEED)
    bad_s, good_s = rng.sample(bad, n), rng.sample(good, n)

    def stats(urls):
        p = [urlparse(normalize_url(u)) for u in urls]
        hosts = [(x.hostname or "") for x in p]
        pct = lambda c: 100 * sum(c) / len(urls)
        sub = [max(0, len(h.split(".")) - 2) for h in hosts]
        return hosts, {"https %": pct([x.scheme == "https" for x in p]), "host starts with www. %": pct([h.startswith("www.") for h in hosts]),
                       "has a path %": pct([x.path not in ("", "/") for x in p]), "has a query %": pct([bool(x.query) for x in p]),
                       ">=1 subdomain %": pct([s >= 1 for s in sub]), "mean subdomains": sum(sub) / len(sub)}
    gh, gs = stats(good_s)
    bh, bs = stats(bad_s)
    print(f"sample sizes: phishing {len(bad_s)}, benign {len(good_s)}")
    print(f"{'measure':<26}{'benign (Tranco)':>18}{'phishing (PhishTank)':>22}")
    for k in gs:
        print(f"{k:<26}{gs[k]:>18.2f}{bs[k]:>22.2f}")
    print("\nprobe domains in the training sample:")
    print(f"{'domain':<18}{'benign host == domain':>24}{'benign host == www.domain':>28}{'phishing hosts on domain':>28}")
    for d in ["google.com", "microsoft.com", "github.com", "amazon.com", "wikipedia.org"]:
        print(f"{d:<18}{sum(h == d for h in gh):>24}{sum(h == 'www.' + d for h in gh):>28}{sum(h == d or h.endswith('.' + d) for h in bh):>28}")


if __name__ == "__main__":
    probe()
    training_check()
