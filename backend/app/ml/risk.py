"""Risk engine. Score = model phishing probability x 100. Confidence = probability of the more likely class."""


def level_of(score: float) -> str:
    return "CRITICAL" if score > 80 else "HIGH" if score > 60 else "MEDIUM" if score > 30 else "LOW"


def url_label(p: float) -> str:
    return "Phishing" if p >= 0.6 else "Suspicious" if p >= 0.3 else "Safe"


def confidence(p: float) -> float:
    return max(p, 1 - p)


RECOMMENDATION = {
    "Phishing": "Do not open this link or enter any credentials. If you already did, change that account's password and report the link.",
    "Suspicious": "Treat this link with caution. Check the address carefully and reach the site by typing it yourself or using a saved bookmark.",
    "Safe": "No strong phishing signals were found in the URL text. Stay alert: this check does not look at the page itself.",
}
