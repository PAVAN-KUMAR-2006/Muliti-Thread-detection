"""QR and file scanners plus .eml/.txt email upload. Uploaded content is only ever read as data, never executed."""
import email
import hashlib
import io
import re
import uuid
import zipfile
from email import policy
from pathlib import Path
import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from . import models
from .config import settings
from .database import get_db
from .deps import get_current_user
from .routes_auth import limiter
from .routes_data import ScanSummary
from .routes_scan import RECOMMEND, IndicatorOut, ScanResult, save_scan, text_scan, url_analysis, url_details

router = APIRouter(prefix="/api/scan", tags=["scan"])
MAX_FILE, MAX_IMG = 5 * 1024 * 1024, 5 * 1024 * 1024
FILE_TYPES = {"txt", "csv", "eml", "pdf", "docx"}
IMG_MAGIC = (b"\x89PNG", b"\xff\xd8\xff", b"RIFF")  # PNG, JPEG, WEBP


def read_limited(f: UploadFile, limit: int) -> bytes:
    data = f.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File too large. The limit is {limit // (1024 * 1024)} MB.")
    if not data:
        raise HTTPException(422, "The file is empty.")
    return data


def ext_of(f: UploadFile) -> tuple[str, str]:
    name = Path(f.filename or "file").name[:255]
    return name, name.rsplit(".", 1)[-1].lower() if "." in name else ""


def parse_eml(data: bytes):
    msg = email.message_from_bytes(data, policy=policy.default)
    try:
        part = msg.get_body(preferencelist=("plain", "html"))
        body = re.sub(r"<[^>]+>", " ", part.get_content()) if part else ""
    except Exception:
        body = ""
    return str(msg["from"] or ""), str(msg["subject"] or ""), body


@router.post("/email-upload", response_model=ScanResult)
@limiter.limit("20/minute")
def email_upload(request: Request, file: UploadFile = File(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    name, ext = ext_of(file)
    if ext not in ("eml", "txt"):
        raise HTTPException(415, "Upload a .eml or .txt file.")
    data = read_limited(file, 1024 * 1024)
    sender, subject, body = parse_eml(data) if ext == "eml" else ("", "", data.decode("utf-8", "replace"))
    if len(body.strip()) < 3:
        raise HTTPException(422, "No readable email text was found in this file.")
    return text_scan(db, user, "email", "email_model", f"{subject} {body}", subject or body[:200], "email",
                     lambda sid: models.EmailScan(scan_id=sid, sender=sender[:320], subject=subject[:500], body_excerpt=body[:2000]),
                     extra_details={"sender": sender, "subject": subject})


# ---------- QR ----------
def decode_qr(data: bytes) -> str | None:
    if not data.startswith(IMG_MAGIC):
        raise HTTPException(415, "Upload a PNG, JPEG or WEBP image.")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(422, "The image could not be read.")
    if img.shape[0] * img.shape[1] > 25_000_000:
        raise HTTPException(422, "The image dimensions are too large.")
    det = cv2.QRCodeDetector()
    for scale in (1, 2, 0.5):
        text, _, _ = det.detectAndDecode(img if scale == 1 else cv2.resize(img, None, fx=scale, fy=scale))
        if text:
            return text
    return None


def qr_result(db, user, content: str) -> ScanResult:
    content = content.strip()[:2048]
    if re.match(r"^https?://", content, re.I):
        url, p, label, ind, prot, contrib = url_analysis(content)  # same URL service as the website scanner
        return save_scan(db, user, "qr", url, label, p, "url_phishing_model", ind, prot, "URL",
                         lambda sid: models.QrScan(scan_id=sid, decoded_url=content),
                         details={**url_details(url), "decoded": content, "is_url": True})
    expl = "The QR code contains plain text, not a URL, so no URL analysis was run and no risk score was calculated."
    scan = models.Scan(user_id=user.id, scan_type="qr", input_summary=content[:500] or "(empty)", label="Safe", risk_score=0.0,
                       risk_level="LOW", confidence=None, status="completed", explanation=expl,
                       recommendation="Treat the content with care if it asks you to call, pay or sign in somewhere.")
    db.add(scan)
    db.flush()
    db.add(models.QrScan(scan_id=scan.id, decoded_url=content))
    db.commit()
    return ScanResult(**ScanSummary.model_validate(scan).model_dump(), confidence=None, explanation=expl,
                      recommendation=scan.recommendation, indicators=[], predictions=[], protective=[],
                      details={"decoded": content, "is_url": False})


@router.post("/qr", response_model=ScanResult)
@limiter.limit("20/minute")
def scan_qr(request: Request, file: UploadFile = File(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = decode_qr(read_limited(file, MAX_IMG))
    if not content:
        raise HTTPException(422, "No QR code was found in this image. Try a sharper, closer photo.")
    return qr_result(db, user, content)


class QrText(BaseModel):
    content: str = Field(min_length=1, max_length=2048)


@router.post("/qr-text", response_model=ScanResult)
@limiter.limit("20/minute")
def scan_qr_text(request: Request, body: QrText, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return qr_result(db, user, body.content)  # content decoded in the browser from the camera


# ---------- Files ----------
PDF_MARKERS = (b"/JavaScript", b"/JS", b"/OpenAction", b"/Launch", b"/EmbeddedFile")


def extract(ext: str, data: bytes):
    """Returns (text, sender, subject, static_flags). Static parsing only."""
    flags: list[str] = []
    if ext in ("txt", "csv"):
        return data[:200_000].decode("utf-8", "replace"), "", "", flags
    if ext == "eml":
        sender, subject, body = parse_eml(data)
        return f"{subject} {body}", sender, subject, flags
    if ext == "pdf":
        if not data.startswith(b"%PDF"):
            raise HTTPException(415, "This file is not a valid PDF.")
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise HTTPException(422, "Encrypted PDFs cannot be analyzed.")
            parts = []
            for page in reader.pages[:30]:
                parts.append(page.extract_text() or "")
                for a in page.get("/Annots") or []:
                    uri = (a.get_object().get("/A") or {}).get("/URI")
                    if uri:
                        parts.append(f" {uri} ")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(422, "The PDF could not be read.")
        flags = [f"PDF contains {m.decode()} (static marker, not scored)" for m in PDF_MARKERS if m in data]
        return "\n".join(parts), "", "", flags
    if not data.startswith(b"PK"):
        raise HTTPException(415, "This file is not a valid DOCX.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        if sum(i.file_size for i in zf.infolist()) > 50 * 1024 * 1024:
            raise HTTPException(422, "The document expands to an unsafe size.")
        if any(n.lower().endswith("vbaproject.bin") for n in zf.namelist()):
            flags.append("Document contains a VBA macro project (static marker, not scored)")
        import docx
        doc = docx.Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells]
        parts += [f" {r.target_ref} " for r in doc.part.rels.values() if r.reltype.endswith("/hyperlink")]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "The DOCX file could not be read.")
    return "\n".join(parts), "", "", flags


@router.post("/file", response_model=ScanResult)
@limiter.limit("10/minute")
def scan_file(request: Request, file: UploadFile = File(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    name, ext = ext_of(file)
    if ext not in FILE_TYPES:
        raise HTTPException(415, "Unsupported file type. Use TXT, CSV, EML, PDF or DOCX.")
    data = read_limited(file, MAX_FILE)
    text, sender, subject, flags = extract(ext, data)
    if len(text.strip()) < 3:
        raise HTTPException(422, "No readable text was found in this file.")
    sha = hashlib.sha256(data).hexdigest()
    folder = Path(settings.upload_dir) / str(user.id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{uuid.uuid4().hex}.bin").write_bytes(data)  # stored under a random name, never executed or served
    return text_scan(db, user, "file", "email_model", text, name, "email",
                     lambda sid: models.FileScan(scan_id=sid, filename=name, size_bytes=len(data), sha256=sha),
                     extra_ind=[IndicatorOut(name=f, severity="low", weight=0.3) for f in flags],
                     extra_details={"file": {"name": name, "type": ext, "size": len(data), "sha256": sha}, "sender": sender, "subject": subject})
