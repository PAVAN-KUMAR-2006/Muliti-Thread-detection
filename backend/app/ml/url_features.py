"""Lexical URL features. Pure string analysis: the URL is never fetched and no WHOIS/DNS lookups are made."""
import math
import re
from collections import Counter
from urllib.parse import parse_qsl, urlparse

KEYWORDS = ("login", "signin", "verify", "account", "update", "secure", "bank", "confirm", "password",
            "paypal", "wallet", "billing", "suspend", "unlock", "invoice", "support")
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "buff.ly", "cutt.ly", "rb.gy"}
IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

FEATURES = (
    "url_length", "hostname_length", "path_length", "query_length", "num_dots", "num_hyphens", "num_underscores",
    "num_digits", "digit_ratio", "num_special_chars", "has_at_symbol", "num_query_params", "num_subdomains",
    "has_ip_host", "uses_https", "has_port", "suspicious_keywords", "url_entropy", "host_entropy", "path_depth",
    "tld_length", "longest_host_label", "host_digit_count", "is_shortener", "has_punycode",
    "num_percent_encoded", "double_slash_in_path",
)

DESCRIBE = {
    "url_length": "URL length ({v:g} characters)", "hostname_length": "Hostname length ({v:g} characters)",
    "path_length": "Path length ({v:g} characters)", "query_length": "Query string length ({v:g} characters)",
    "num_dots": "Number of dots ({v:g})", "num_hyphens": "Number of hyphens ({v:g})",
    "num_underscores": "Number of underscores ({v:g})", "num_digits": "Number of digits ({v:g})",
    "digit_ratio": "Share of digits in the URL ({v:.0%})", "num_special_chars": "Special characters such as @ ! $ * # ({v:g})",
    "has_at_symbol": "Contains an @ symbol", "num_query_params": "Query parameters ({v:g})",
    "num_subdomains": "Subdomain levels ({v:g})", "has_ip_host": "IP address used instead of a domain name",
    "uses_https": "HTTPS scheme", "has_port": "Explicit port number", "suspicious_keywords": "Sensitive keywords in the URL ({v:g})",
    "url_entropy": "Character randomness of the URL ({v:.2f} bits)", "host_entropy": "Character randomness of the hostname ({v:.2f} bits)",
    "path_depth": "Path depth ({v:g} levels)", "tld_length": "Top-level domain length ({v:g})",
    "longest_host_label": "Longest hostname label ({v:g} characters)", "host_digit_count": "Digits in the hostname ({v:g})",
    "is_shortener": "Known link-shortener domain", "has_punycode": "Punycode (xn--) hostname",
    "num_percent_encoded": "Percent-encoded characters ({v:g})", "double_slash_in_path": "Double slash inside the path",
}


class InvalidURL(ValueError):
    pass


def normalize(raw: str):
    u = (raw or "").strip()
    if not u or re.search(r"\s", u):
        raise InvalidURL("Enter a URL without spaces, for example https://example.com.")
    if "://" not in u:
        u = "http://" + u  # no scheme given, so it is treated as plain http
    try:
        p = urlparse(u)
        host, _ = p.hostname, p.port
    except ValueError:
        raise InvalidURL("That URL could not be parsed. Check it and try again.")
    if p.scheme not in ("http", "https"):
        raise InvalidURL("Only http and https URLs can be analyzed.")
    if not host or "." not in host:
        raise InvalidURL("Enter a valid URL, for example https://example.com.")
    return u, p


def entropy(s: str) -> float:
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values()) if n else 0.0


def extract(raw: str) -> dict[str, float]:
    url, p = normalize(raw)
    host, path, query = p.hostname.lower(), p.path or "", p.query or ""
    labels = host.split(".")
    is_ip = bool(IP_RE.match(host))
    low = url.lower()
    digits = sum(c.isdigit() for c in url)
    f = {
        "url_length": len(url), "hostname_length": len(host), "path_length": len(path), "query_length": len(query),
        "num_dots": url.count("."), "num_hyphens": url.count("-"), "num_underscores": url.count("_"),
        "num_digits": digits, "digit_ratio": digits / len(url),
        "num_special_chars": sum(url.count(c) for c in "@!$*#~,;+"), "has_at_symbol": int("@" in url),
        "num_query_params": len(parse_qsl(query, keep_blank_values=True)),
        "num_subdomains": 0 if is_ip else max(0, len(labels) - 2),  # naive: multi-part TLDs such as co.uk count one extra
        "has_ip_host": int(is_ip), "uses_https": int(p.scheme == "https"), "has_port": int(p.port is not None),
        "suspicious_keywords": sum(k in low for k in KEYWORDS), "url_entropy": entropy(url), "host_entropy": entropy(host),
        "path_depth": len([x for x in path.split("/") if x]), "tld_length": 0 if is_ip else len(labels[-1]),
        "longest_host_label": max(len(x) for x in labels), "host_digit_count": sum(c.isdigit() for c in host),
        "is_shortener": int(host in SHORTENERS), "has_punycode": int("xn--" in host),
        "num_percent_encoded": url.count("%"), "double_slash_in_path": int("//" in path),
    }
    return {k: float(f[k]) for k in FEATURES}
