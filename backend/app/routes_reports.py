import io
import uuid
from xml.sax.saxutils import escape
from fastapi import APIRouter, Depends, Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models
from .database import get_db
from .deps import get_current_user, get_owned_scan

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/scan/{scan_id}/pdf")
def scan_pdf(scan_id: uuid.UUID, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_owned_scan(scan_id, user, db)  # same ownership check as the history API
    inds = db.scalars(select(models.ThreatIndicator).where(models.ThreatIndicator.scan_id == s.id).order_by(models.ThreatIndicator.weight.desc())).all()
    preds = db.scalars(select(models.ModelPrediction).where(models.ModelPrediction.scan_id == s.id)).all()
    st = getSampleStyleSheet()
    P = lambda t, style="BodyText": Paragraph(escape(str(t)), st[style])
    conf = "n/a" if s.confidence is None else f"{s.confidence:.0%}"
    story = [P("Sentinel Security Report", "Title"), P(f"Prepared for {user.name} ({user.email})"), Spacer(1, 8 * mm)]
    rows = [["Scan ID", str(s.id)], ["Type", s.scan_type], ["Date", s.created_at.strftime("%Y-%m-%d %H:%M UTC")],
            ["Input", s.input_summary[:300]], ["Classification", s.label], ["Risk score", f"{s.risk_score:.0f}/100 ({s.risk_level})"], ["Model confidence", conf]]
    t = Table([[P(a, "Heading5"), P(b)] for a, b in rows], colWidths=[40 * mm, 130 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [t, Spacer(1, 6 * mm), P("Explanation", "Heading3"), P(s.explanation or "None recorded."),
              P("Detected indicators", "Heading3")]
    story += [P(f"- {i.name} ({i.severity})") for i in inds] or [P("None recorded.")]
    story += [P("Machine learning", "Heading3")]
    story += [P(f"- {p.model_name} v{p.model_version}: probability {p.probability:.1%}") for p in preds] or [P("No model was run for this scan.")]
    story += [P("Recommendation", "Heading3"), P(s.recommendation or "None recorded.")]
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, title="Sentinel Security Report").build(story)
    return Response(buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="sentinel-scan-{str(s.id)[:8]}.pdf"'})
