"""Feature extraction shared by the training scripts and the API, so both see identical inputs."""
import ipaddress
import math
import re
from collections import Counter
from urllib.parse import parse_qsl, urlparse

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
KEYWORDS = ("login", "signin", "verify", "secure", "account", "update", "bank", "confirm", "password",
            "wallet", "paypal", "invoice", "support", "bonus", "free", "billing", "unlock", "suspend")
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "cutt.ly", "rb.gy"}

URL_FEATURES = ["url_length", "host_length", "path_length", "query_length", "num_dots", "num_hyphens",
                "num_subdomains", "num_digits", "num_special_chars", "num_params", "num_suspicious_chars",
                "has_ip_host", "https", "keyword_count", "url_entropy", "host_entropy", "host_digit_ratio",
                "is_shortener", "tld_length", "non_default_port", "has_punycode", "path_depth", "has_at_symbol"]

LABELS = {
    "url_length": "URL length", "host_length": "Hostname length", "path_length": "Path length",
    "query_length": "Query string length", "num_dots": "Number of dots", "num_hyphens": "Number of hyphens",
    "num_subdomains": "Number of subdomains", "num_digits": "Number of digits",
    "num_special_chars": "Special characters", "num_params": "Query parameters",
    "num_suspicious_chars": "Unusual characters (@ % ~ $ ! etc.)", "has_ip_host": "IP address used as host",
    "https": "HTTPS used", "keyword_count": "Sensitive keywords in URL", "url_entropy": "URL randomness (entropy)",
    "host_entropy": "Hostname randomness (entropy)", "host_digit_ratio": "Digit share of hostname",
    "is_shortener": "Known link shortener", "tld_length": "Top-level domain length",
    "non_default_port": "Non-standard port", "has_punycode": "Punycode (xn--) hostname",
    "path_depth": "Path depth", "has_at_symbol": "@ symbol in URL",
}


def entropy(s: str) -> float:
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    return raw if "://" in raw else "http://" + raw


def url_features(raw: str) -> dict[str, float]:
    url = normalize_url(raw)
    p = urlparse(url)
    host = (p.hostname or "").lower()
    parts = [x for x in host.split(".") if x]
    try:
        ipaddress.ip_address(host)
        is_ip = 1
    except ValueError:
        is_ip = 0
    try:
        port = p.port
    except ValueError:
        port = -1
    low = url.lower()
    return {
        "url_length": len(url), "host_length": len(host), "path_length": len(p.path), "query_length": len(p.query),
        "num_dots": url.count("."), "num_hyphens": url.count("-"),
        "num_subdomains": max(0, len(parts) - 2) if not is_ip else 0,
        "num_digits": sum(c.isdigit() for c in url), "num_special_chars": sum(not c.isalnum() for c in url),
        "num_params": len(parse_qsl(p.query)), "num_suspicious_chars": sum(url.count(c) for c in "@%~$!*;,'()"),
        "has_ip_host": is_ip, "https": int(p.scheme == "https"), "keyword_count": sum(k in low for k in KEYWORDS),
        "url_entropy": entropy(url), "host_entropy": entropy(host),
        "host_digit_ratio": sum(c.isdigit() for c in host) / max(1, len(host)),
        "is_shortener": int(host in SHORTENERS), "tld_length": len(parts[-1]) if parts else 0,
        "non_default_port": int(port not in (None, 80, 443)), "has_punycode": int("xn--" in host),
        "path_depth": len([s for s in p.path.split("/") if s]), "has_at_symbol": int("@" in url),
    }


def find_urls(text: str, limit: int = 5) -> list[str]:
    return list(dict.fromkeys(URL_RE.findall(text)))[:limit]


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = URL_RE.sub(" urltoken ", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


SIGNALS = {
    "urgency": ("urgent", "immediately", "act now", "expires", "within 24 hours", "final notice", "last chance", "suspended"),
    "financial": ("you have won", "prize", "lottery", "refund", "bank account", "wire transfer", "payment", "₹", "invoice"),
    "credentials": ("password", "verify your account", "log in", "login", "otp", "kyc", "pin", "confirm your identity"),
}


def language_signals(text: str) -> list[str]:
    """Plain keyword signals shown as extra context. They are NOT part of the model score."""
    low = text.lower()
    out = []
    for cat, words in SIGNALS.items():
        hit = [w for w in words if w in low]
        if hit:
            out.append(f"Language signal (not scored) - {cat}: {', '.join(hit[:4])}")
    return out
