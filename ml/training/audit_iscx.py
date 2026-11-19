"""READ-ONLY audit of the ISCX-URL2016 dataset (benign vs phishing URL structure). Prints a report and nothing else:
no files written, no network, no database, no model or metrics access, no training.

Put the dataset in  ml/datasets/iscx/  either as the original .zip (read in memory, never extracted) or as the extracted
folder. The script discovers every .csv/.tsv/.txt file there (and inside any .zip), works out the layout of each one,
and assigns classes from a label column or, failing that, from the file name (benign / phish / malware / spam / defacement).
Run: docker compose exec -e PYTHONPATH=/app backend python /ml/training/audit_iscx.py"""
import argparse
import csv
import random
import re
import statistics
import sys
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from app.ml.features import URL_FEATURES, normalize_url, url_features

DEFAULT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "iscx"
TEXT_EXT = {".csv", ".txt", ".tsv"}
URL_COLS = {"url", "urls", "link", "website"}
LABEL_COLS = {"label", "type", "class", "category", "status", "url_type_obf_type"}
MULTI = {"co", "com", "org", "net", "gov", "edu", "ac", "or", "ne", "go", "gv", "ltd", "plc", "nom", "sch"}
URLISH = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|(?:[\w-]+\.)+[a-z]{2,}(?:[:/?#]|$))", re.I)
LABELED = re.compile(r"^(.+?),\s*(benign|legit\w*|phish\w*|malware|spam|defacement|[01])\s*$", re.I)
WATCH = ["path_length", "url_length", "num_special_chars", "path_depth", "num_dots", "num_subdomains", "query_length",
         "num_params", "https", "host_length", "url_entropy", "host_entropy"]
CHECKS = {
    "login pages": re.compile(r"(log[-_]?in|sign[-_]?in|sign[-_]?on|logon|/auth\b|sso)", re.I),
    "search / query URLs": re.compile(r"([?&](q|query|s|search|keyword|keywords)=|/search\b)", re.I),
    "account / profile pages": re.compile(r"/(account|accounts|profile|profiles|user|users|member|members|my|settings|dashboard)(/|$|\?|\.)", re.I),
    "docs / blog / article URLs": re.compile(r"/(docs?|documentation|blog|blogs|article|articles|news|wiki|post|posts|help|faq|guide|manual|tutorials?)(/|$|\?|\.)", re.I),
}


def norm_class(text):
    t = (text or "").lower()
    for key, cls in (("benign", "benign"), ("legit", "benign"), ("phish", "phishing"), ("malware", "malware"),
                     ("spam", "spam"), ("deface", "defacement")):
        if key in t:
            return cls
    return None


def sources(root):
    if not root.exists():
        sys.exit(f"Folder not found: {root}\nCreate it and put the ISCX-URL2016 files (or the .zip) inside.")
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        ext = p.suffix.lower()
        if ext in TEXT_EXT:
            yield str(p.relative_to(root)), p.read_bytes()
        elif ext == ".zip":
            with zipfile.ZipFile(p) as z:
                for n in sorted(z.namelist()):
                    if n.startswith("__MACOSX") or n.endswith("/") or Path(n).suffix.lower() not in TEXT_EXT:
                        continue
                    yield f"{p.name}!{n}", (z.read(n) if z.getinfo(n).file_size <= 300_000_000 else None)


def read_urls(name, data):
    """Returns ([(url, class_or_None)], note). Handles: header with a URL column, 'url,label' lines, one URL per line."""
    if data is None:
        return [], "skipped: file larger than 300 MB"
    lines = [l.strip() for l in data.decode("utf-8-sig", errors="replace").splitlines() if l.strip()]
    if not lines:
        return [], "skipped: empty"
    hint = norm_class(Path(name.split("!")[-1]).stem)
    first = [c.strip().strip('"').lower() for c in next(csv.reader([lines[0]]))]
    ucol = next((i for i, c in enumerate(first) if c in URL_COLS), None)
    if ucol is not None:
        lcol = next((i for i, c in enumerate(first) if c in LABEL_COLS), None)
        rows = []
        for r in csv.reader(lines[1:]):
            if len(r) > ucol and r[ucol].strip():
                rows.append((r[ucol].strip(), (norm_class(r[lcol]) if lcol is not None and len(r) > lcol else None) or hint))
        return rows, f"header, URL column '{first[ucol]}', label column '{first[lcol] if lcol is not None else 'none'}'"
    sample = lines[:200]
    labeled = lambda l: (m := LABELED.match(l)) is not None and URLISH.match(m.group(1).strip().strip('"')) is not None  # the first part must look like a URL
    if sum(map(labeled, sample)) > len(sample) / 2:
        rows = [(m.group(1).strip().strip('"'), norm_class(m.group(2)) or hint) for m in map(LABELED.match, filter(labeled, lines))]
        return rows, "headerless 'url,label' lines"
    if sum(bool(URLISH.match(l.strip('"'))) for l in sample) > 0.8 * len(sample):
        return [(l.strip('"'), hint) for l in lines], "headerless, one URL per line"
    return [], f"skipped: no URL column recognised (first row: {lines[0][:90]!r})"


def reg_domain(host):
    if not host or re.fullmatch(r"[\d.]+", host) or ":" in host:
        return host
    parts = host.split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in MULTI:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def parse(u):
    has_scheme = "://" in u
    try:
        p = urlparse(u if has_scheme else "http://" + u)
        host, port = (p.hostname or "").lower(), p.port
        reg = reg_domain(host)
        subs = 0 if re.fullmatch(r"[\d.]+", host) else max(0, len(host.split(".")) - len(reg.split(".")))
        return dict(url=u, scheme=p.scheme.lower() if has_scheme else "", host=host, reg=reg, path=p.path, query=p.query,
                    fragment=p.fragment, userinfo=p.username is not None or p.password is not None, port=port is not None,
                    subs=subs, depth=len([s for s in p.path.split("/") if s]))
    except ValueError:
        return None


def describe(urls):
    uniq = list(dict.fromkeys(urls))
    parsed = [x for x in map(parse, uniq) if x]
    n = len(parsed) or 1
    pct = lambda f: f"{100 * sum(1 for x in parsed if f(x)) / n:.1f}%"
    lengths = [len(x["url"]) for x in parsed] or [0]
    regs = Counter(x["reg"] for x in parsed)
    per = list(regs.values()) or [0]
    top10 = sum(c for _, c in regs.most_common(10))
    depth = Counter(min(x["depth"], 5) for x in parsed)
    rows = [("total rows", f"{len(urls):,}"), ("unique URLs", f"{len(uniq):,}"),
            ("duplicate rows", f"{100 * (1 - len(uniq) / max(1, len(urls))):.1f}%"), ("unparseable URLs", f"{len(uniq) - len(parsed):,}"),
            ("unique registered domains (approx.)", f"{len(regs):,}"),
            ("URLs with an explicit scheme", pct(lambda x: x["scheme"] != "")),
            ("  http", pct(lambda x: x["scheme"] == "http")), ("  https", pct(lambda x: x["scheme"] == "https")),
            ("host starts with www.", pct(lambda x: x["host"].startswith("www."))),
            ("bare host / homepage (no path/query/fragment)", pct(lambda x: x["path"] in ("", "/") and not x["query"] and not x["fragment"])),
            ("path is just '/' (trailing slash only)", pct(lambda x: x["path"] == "/")),
            ("has a real path (inner page)", pct(lambda x: x["path"] not in ("", "/"))),
            ("has a query string", pct(lambda x: bool(x["query"]))), ("has a fragment", pct(lambda x: bool(x["fragment"]))),
            ("username/password in URL", pct(lambda x: x["userinfo"])), ("explicit port", pct(lambda x: x["port"])),
            ("any subdomain (incl. www)", pct(lambda x: x["subs"] >= 1)),
            ("subdomain other than www", pct(lambda x: x["subs"] - int(x["host"].startswith("www.")) >= 1)),
            ("mean number of subdomains", f"{sum(x['subs'] for x in parsed) / n:.2f}"),
            ("URL length: median", f"{statistics.median(lengths):.0f}"), ("URL length: mean", f"{statistics.mean(lengths):.1f}")]
    rows += [(f"path depth {'5+' if d == 5 else d}", f"{100 * depth.get(d, 0) / n:.1f}%") for d in range(6)]
    rows += [(f"content check: {k}", pct(lambda x, r=r: bool(r.search(x["host"] + x["path"] + "?" + x["query"])))) for k, r in CHECKS.items()]
    rows += [("URLs per registered domain: mean / median / max", f"{statistics.mean(per):.1f} / {statistics.median(per):.0f} / {max(per)}"),
             ("share of URLs from the top 10 domains", f"{100 * top10 / n:.1f}%")]
    return rows, uniq, parsed, regs


def show_table(title, a_name, a_rows, b_name, b_rows):
    print(f"\n== {title}\n{'measure':<52}{a_name:>16}{b_name:>16}")
    for (k, av), (_, bv) in zip(a_rows, b_rows):
        print(f"{k:<52}{av:>16}{bv:>16}")


def separability(ben, phi):
    try:
        import numpy as np
        from sklearn.metrics import roc_auc_score, roc_curve
    except ImportError as e:
        print(f"\n== SINGLE-FEATURE SEPARABILITY skipped: missing package ({e.name}). Install scikit-learn and numpy in the backend image.")
        return
    X, y = [], []
    for urls, label in ((ben, 0), (phi, 1)):
        for u in urls:
            try:
                f = url_features(normalize_url(u))
                X.append([f[n] for n in URL_FEATURES]); y.append(label)
            except Exception:
                continue
    X, y = np.array(X, float), np.array(y)
    print(f"\n== SINGLE-FEATURE SEPARABILITY ({int((y == 0).sum()):,} benign vs {int((y == 1).sum()):,} phishing unique URLs; * = features you asked about)")
    print("AUC 0.5 = no signal, 1.0 = this one feature alone separates the classes. 'sep' = max(AUC, 1-AUC). 'bal.acc' = best single-threshold balanced accuracy.")
    out = []
    for i, name in enumerate(URL_FEATURES):
        x = X[:, i]
        if np.ptp(x) == 0:
            out.append((name, 0.5, 0.5, 0.5, "constant")); continue
        auc = float(roc_auc_score(y, x)); s = 1 if auc >= 0.5 else -1
        fpr, tpr, _ = roc_curve(y, s * x)
        out.append((name, auc, max(auc, 1 - auc), float(np.max((tpr + 1 - fpr) / 2)), "higher in phishing" if s == 1 else "higher in benign"))
    print(f"{'feature':<24}{'AUC':>8}{'sep':>8}{'bal.acc':>9}  direction")
    for name, auc, sep, bal, d in sorted(out, key=lambda t: -t[2]):
        print(f"{'*' if name in WATCH else ' '}{name:<23}{auc:>8.3f}{sep:>8.3f}{bal:>9.3f}  {d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(DEFAULT_DIR))
    root = Path(ap.parse_args().dir)
    print(f"== 1. FILES FOUND under {root}")
    by_class, inventory = {}, []
    for name, data in sources(root):
        rows, note = read_urls(name, data)
        c = Counter(cls or "unclassified" for _, cls in rows)
        print(f"- {name}: {len(rows):,} URLs ({note}); classes: {dict(c) or '-'}")
        for url, cls in rows:
            by_class.setdefault(cls or "unclassified", []).append(url)
    print("\nrows per class across all files: " + ", ".join(f"{k} {len(v):,}" for k, v in sorted(by_class.items())))
    if not by_class.get("benign") or not by_class.get("phishing"):
        sys.exit("\nNeed both a benign and a phishing class. Check the file list above: a file must have a URL column or one URL per line, "
                 "and a name or label containing 'benign' / 'phish'.")

    b_rows, b_uniq, b_parsed, b_regs = describe(by_class["benign"])
    p_rows, p_uniq, p_parsed, p_regs = describe(by_class["phishing"])
    show_table("2. STRUCTURE (computed over unique URLs; domains are approximate: last two labels, no public-suffix list)",
               "benign", b_rows, "phishing", p_rows)
    for cls, parsed in (("benign", b_parsed), ("phishing", p_parsed)):
        regs = Counter(x["reg"] for x in parsed)
        print(f"\n== top 20 registered domains, {cls} ({len(parsed):,} URLs)")
        for d, c in regs.most_common(20):
            print(f"   {d:<40}{c:>7}  {100 * c / max(1, len(parsed)):5.1f}%")
    if len([x for x in b_parsed if not x["scheme"]]) / max(1, len(b_parsed)) > 0.05 or len([x for x in p_parsed if not x["scheme"]]) / max(1, len(p_parsed)) > 0.05:
        print("\nWARNING: more than 5% of URLs in a class have no explicit scheme. normalize_url() adds http:// to those, so the 'https' feature "
              "partly reflects how the dataset was written, not the site.")

    separability(b_uniq, p_uniq)

    both = (set(b_regs) & set(p_regs)) - {""}
    b_on = sum(c for d, c in b_regs.items() if d in both); p_on = sum(c for d, c in p_regs.items() if d in both)
    print(f"\n== DOMAIN LEAKAGE (approximate registered domains)\nexact same URL in both classes: {len(set(b_uniq) & set(p_uniq)):,}")
    print(f"registered domains in both classes: {len(both):,} = {100 * len(both) / max(1, len(b_regs)):.1f}% of benign domains, "
          f"{100 * len(both) / max(1, len(p_regs)):.1f}% of phishing domains")
    print(f"benign URLs on those domains: {100 * b_on / max(1, len(b_parsed)):.1f}%   phishing URLs on those domains: {100 * p_on / max(1, len(p_parsed)):.1f}%")
    print("top 20 overlapping domains (appearing in a class does NOT make a domain benign or malicious):")
    print(f"   {'domain':<40}{'benign':>8}{'phishing':>10}")
    for d in sorted(both, key=lambda d: -(b_regs[d] + p_regs[d]))[:20]:
        print(f"   {d:<40}{b_regs[d]:>8}{p_regs[d]:>10}")

    rng = random.Random(42)
    for cls, uniq in (("benign", b_uniq), ("phishing", p_uniq)):
        print(f"\n== random sample of {cls} URLs (seed 42)")
        for u in rng.sample(uniq, min(8, len(uniq))):
            print("   " + u[:130])
    others = {k: len(v) for k, v in by_class.items() if k not in ("benign", "phishing")}
    print(f"\n== other classes (counted only, not analysed): {others or 'none'}")
    print("\nNotes: content checks are keyword patterns on host+path+query, not verified page types. Registered domains are approximate.")


if __name__ == "__main__":
    main()
