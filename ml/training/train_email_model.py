"""Train the email spam model (TF-IDF + Logistic Regression) on the Apache SpamAssassin public corpus.
The corpus has spam and ham only, so the model predicts spam probability; 'Phishing' is decided in the API
by combining a high spam probability with a URL flagged by the URL model.
Run: docker compose exec -e PYTHONPATH=/app backend python /ml/training/train_email_model.py"""
import email
import io
import re
import sys
import tarfile
from email import policy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from train_utils import DATA, download, train_text  # noqa: E402

BASE = "https://spamassassin.apache.org/old/publiccorpus/"
SETS = [("20030228_spam.tar.bz2", 1), ("20030228_easy_ham.tar.bz2", 0), ("20030228_hard_ham.tar.bz2", 0), ("20050311_spam_2.tar.bz2", 1)]


def body_of(msg) -> str:
    try:
        part = msg.get_body(preferencelist=("plain", "html"))
        return re.sub(r"<[^>]+>", " ", part.get_content()) if part else ""
    except Exception:
        return ""


texts, labels = [], []
for name, label in SETS:
    tar = tarfile.open(fileobj=io.BytesIO(download(BASE + name, DATA / name).read_bytes()), mode="r:bz2")
    for m in tar.getmembers():
        f = tar.extractfile(m) if m.isfile() and not m.name.endswith("cmds") else None
        if f:
            msg = email.message_from_bytes(f.read(), policy=policy.default)
            text = f"{msg['subject'] or ''} {body_of(msg)[:5000]}".strip()
            if text:
                texts.append(text); labels.append(label)
train_text("email_model", texts, labels, "TF-IDF + Logistic Regression on Apache SpamAssassin public corpus")
