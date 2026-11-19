"""Train the SMS/message spam model (TF-IDF + Logistic Regression) on the UCI SMS Spam Collection.
Run: docker compose exec -e PYTHONPATH=/app backend python /ml/training/train_sms_model.py"""
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from train_utils import DATA, download, train_text  # noqa: E402

zf = zipfile.ZipFile(download("https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip", DATA / "sms.zip"))
texts, labels = [], []
for line in io.TextIOWrapper(zf.open("SMSSpamCollection"), encoding="utf-8", errors="ignore"):
    tag, _, text = line.partition("\t")
    if tag in ("ham", "spam") and text.strip():
        texts.append(text.strip()); labels.append(int(tag == "spam"))
train_text("sms_model", texts, labels, "TF-IDF + Logistic Regression on UCI SMS Spam Collection")
