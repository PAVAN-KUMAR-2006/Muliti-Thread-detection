"""History export (CSV, Excel, PDF). Uses the same scan_conditions() as the History page, so an export
contains exactly what the filtered History view shows, and only ever the signed-in user's scans."""
import csv
import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from . import models
from .database import get_db
from .deps import get_current_user
from .routes_data import scan_conditions

router = APIRouter(prefix="/api/history/export", tags=["export"])
MAX_ROWS = 5000
HEAD = ["Date (UTC)", "Scanner", "Input / file", "Result", "Risk score", "Risk level", "Confidence", "Status", "Scan ID"]
LEVEL_COLOR = {"LOW": "#059669", "MEDIUM": "#b7791f", "HIGH": "#dc2626", "CRITICAL": "#991b1b"}


def export_filters(q: str = Query("", max_length=200), type: str | None = None, threat: str | None = None,
                   risk: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None) -> dict:
    return {"q": q, "type": type, "threat": threat, "risk": risk, "date_from": date_from, "date_to": date_to}


def safe(v) -> str:
    """Neutralise spreadsheet formula injection: user-controlled text must never start a formula."""
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def load(user, db, f):
    S = models.Scan
    conds = scan_conditions(user, **f)
    total = db.scalar(select(func.count()).select_from(S).where(*conds)) or 0
    scans = db.scalars(select(S).where(*conds).order_by(S.created_at.desc(), S.id).limit(MAX_ROWS)).all()
    rows = [[s.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"), s.scan_type, s.input_summary, s.label,
             round(s.risk_score, 1), s.risk_level, "" if s.confidence is None else round(s.confidence, 3), s.status, str(s.id)]
            for s in scans]
    return rows, total


def describe(f) -> list[str]:
    out = []
    if f["type"]: out.append(f"Scanner: {f['type']}")
    if f["threat"]: out.append(f"Detection: {f['threat']}")
    if f["risk"]: out.append(f"Risk level: {f['risk'].upper()}")
    if f["q"]: out.append(f"Search: {f['q']}")
    if f["date_from"]: out.append(f"From: {f['date_from']:%Y-%m-%d}")
    if f["date_to"]: out.append(f"To: {f['date_to']:%Y-%m-%d}")
    return out or ["None (all scans)"]


def attach(content: bytes, media: str, ext: str) -> Response:
    name = f"sentinel-history-{datetime.now(timezone.utc):%Y%m%d}.{ext}"
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/csv")
def export_csv(f: dict = Depends(export_filters), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows, _ = load(user, db, f)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEAD)
    for r in rows:
        w.writerow([safe(c) if isinstance(c, str) else c for c in r])
    return attach(buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", "csv")  # BOM so Excel reads UTF-8


@router.get("/excel")
def export_excel(f: dict = Depends(export_filters), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows, total = load(user, db, f)
    wb = Workbook()
    ws = wb.active
    ws.title = "Scan history"
    ws.append(HEAD)
    for r in rows:
        ws.append([safe(c) if isinstance(c, str) else c for c in r])
    for c in ws[1]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F")
        c.alignment = Alignment(vertical="center")
    for i, width in enumerate([18, 11, 60, 13, 11, 12, 12, 11, 38], 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    info = wb.create_sheet("Summary")
    counts: dict[str, int] = {}
    for r in rows: counts[r[3]] = counts.get(r[3], 0) + 1
    for line in [["Sentinel scan history export"], ["User", f"{user.name} <{user.email}>"],
                 ["Generated (UTC)", f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M}"], ["Filters", "; ".join(describe(f))],
                 ["Scans matching filters", total], ["Scans in this file", len(rows)], [], ["Result", "Count"], *sorted(counts.items())]:
        info.append([safe(c) if isinstance(c, str) else c for c in line])
    info["A1"].font = Font(bold=True, size=14)
    info.column_dimensions["A"].width, info.column_dimensions["B"].width = 26, 48
    buf = io.BytesIO()
    wb.save(buf)
    return attach(buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx")


@router.get("/pdf")
def export_pdf(f: dict = Depends(export_filters), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows, total = load(user, db, f)
    st = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=st["BodyText"], fontSize=8, leading=10)
    P = lambda t, style=None: Paragraph(escape(str(t)), style or st["BodyText"])
    counts: dict[str, int] = {}
    for r in rows: counts[r[3]] = counts.get(r[3], 0) + 1
    story = [P("Sentinel - Scan History Report", st["Title"]),
             P(f"Prepared for {user.name} ({user.email}) on {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"),
             P("Filters: " + "; ".join(describe(f))),
             P(f"{total} scans match" + (f" - showing the newest {len(rows)}" if total > len(rows) else "") + ". Summary: " +
               (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "no scans")), Spacer(1, 5 * mm)]
    data = [["Date (UTC)", "Scanner", "Input / file", "Result", "Risk", "Level", "Conf."]]
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("FONTSIZE", (0, 0), (-1, 0), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")])]
    for i, r in enumerate(rows, 1):
        data.append([P(r[0], cell), P(r[1], cell), P(r[2][:160], cell), P(r[3], cell), f"{r[4]:.0f}", r[5], "-" if r[6] == "" else f"{r[6]:.0%}"])
        style += [("TEXTCOLOR", (5, i), (5, i), colors.HexColor(LEVEL_COLOR.get(r[5], "#000000"))), ("FONTSIZE", (4, i), (6, i), 8)]
    if not rows:
        story.append(P("No scans match these filters."))
    else:
        t = Table(data, colWidths=[30 * mm, 22 * mm, 110 * mm, 28 * mm, 14 * mm, 22 * mm, 16 * mm], repeatRows=1)
        t.setStyle(TableStyle(style))
        story.append(t)

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(15 * mm, 8 * mm, "Sentinel - confidential, contains your scan data")
        canvas.drawRightString(landscape(A4)[0] - 15 * mm, 8 * mm, f"Page {doc.page}")

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                      title="Sentinel scan history").build(story, onFirstPage=footer, onLaterPages=footer)
    return attach(buf.getvalue(), "application/pdf", "pdf")
