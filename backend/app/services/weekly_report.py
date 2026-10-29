"""Owner's weekly report (PDF): the six headline numbers, the five actions, where money leaks, supply risks and the discount finding.
English only: the PDF engine in use cannot shape Arabic text, so this report is not offered in Arabic."""
from __future__ import annotations
import io
from datetime import datetime
from pathlib import Path

LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo.png"


def _latin(t) -> str:
    """The PDF font has no Arabic glyphs: keep Latin text, digits and punctuation, and drop Arabic runs instead of printing black boxes."""
    import re
    t = "".join(ch for ch in str(t or "") if ord(ch) < 0x250 or ch in "\u2013\u2014\u2019\u201c\u201d\u2026")
    return re.sub(r"\s{2,}", " ", re.sub(r"\s+([,;:)])", r"\1", t)).strip(" -")


def _egp(v) -> str:
    return "-" if v is None else f"EGP {v:,.0f}"


def build_pdf(cc: dict, lk: dict, sp: dict, ds: dict, fresh: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    st = getSampleStyleSheet(); INK, GOLD = colors.HexColor("#111827"), colors.HexColor("#94702b")
    h2 = ParagraphStyle("h2", parent=st["Heading2"], textColor=INK, spaceBefore=10, spaceAfter=4); small = ParagraphStyle("sm", parent=st["Normal"], fontSize=8, textColor=colors.HexColor("#64748b"), leading=10)
    from app.services.company import get_company_name
    comp = get_company_name(db).get("company_name", "Business Gate")
    body = ParagraphStyle("b", parent=st["Normal"], fontSize=9, leading=12)
    buf = io.BytesIO(); doc = SimpleDocTemplate(buf, pagesize=A4, title="MERCHBRAIN weekly report", leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    head = [[Image(str(LOGO), 22 * mm, 22 * mm) if LOGO.exists() else "", [Paragraph("<b>MERCHBRAIN</b> - Weekly report", ParagraphStyle("t", parent=st["Title"], alignment=0, fontSize=18, textColor=INK, spaceAfter=2)),
            Paragraph(f"{comp} - AI Commercial Decision &amp; Profit Recovery Engine", small), Paragraph(f"Generated {datetime.utcnow():%d %b %Y} - data as of {fresh.get('data_as_of')}", small)]]]
    ht = Table(head, colWidths=[26 * mm, 150 * mm]); ht.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, 0), 1, GOLD)]))
    el = [ht, Spacer(1, 8), Paragraph(f"Where is {comp} losing money today, what will happen next, and what should the business do about it?", ParagraphStyle("q", parent=body, fontSize=10, textColor=GOLD))]
    tiles = [[t["label"], _egp(t["value"]) if t["unit"] == "egp" else f"{t['value']:,.0f} {t['unit']}"] for t in cc["tiles"]]
    tt = Table([["Headline", "Value"]] + tiles, colWidths=[110 * mm, 66 * mm]); tt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#cbd5e1")), ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 0), (1, -1), "RIGHT")]))
    el += [Paragraph("Headline numbers", h2), tt, Paragraph("Profit at Risk and Recoverable Profit are estimates; leakage is what already happened in the last 12 months.", small), Paragraph("Top actions this week", h2)]
    for i, a in enumerate(cc["actions"], 1):
        el += [Paragraph(f"<b>{i}. {a['label']}: {_latin(a['title'])}</b><br/>{_latin(a['detail'])}<br/><font color='#64748b'>{a['value_kind']}: {_egp(a['value_egp'])} - urgency {a['urgency']}</font>", body), Spacer(1, 5)]
    lt = Table([["Leak", "Basis", "12 months", "Share"]] + [[i["label"], i["basis"].title(), _egp(i["value"]), f"{i['share']:.0%}"] for i in lk["items"]] + [["Total", "", _egp(lk["total"]), ""]], colWidths=[80 * mm, 28 * mm, 40 * mm, 28 * mm])
    lt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#cbd5e1")), ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    el += [Paragraph("Where the money leaks", h2), lt, Paragraph(lk["reconciliation"]["label"], small), Paragraph("Supply readiness", h2)]
    mt = [[_latin(m["material_name"]), _latin(m["main_supplier"]) or "-", f"{(m['late_rate'] or 0):.0%}", f"{m['order_ahead_days']:.0f} d", m["risk"]] for m in sp["materials"][:6]]
    st_ = Table([["Material", "Main supplier", "Late POs", "Order ahead", "Risk"]] + mt, colWidths=[56 * mm, 56 * mm, 20 * mm, 24 * mm, 20 * mm]); st_.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#cbd5e1")), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    el += [st_, Paragraph(sp["limits"][0], small), Paragraph("Discounts", h2), Paragraph(ds["headline"], body), Spacer(1, 4),
           Paragraph(f"Discount given above the {ds['comfort']:.0%} comfort band in 12 months: {_egp(ds['excess_total'])}.", body), Spacer(1, 12),
           Paragraph("All EGP figures marked as estimate, exposure or dependency are not guaranteed savings. Source: company data files imported into MerchBrain.", small)]
    doc.build(el)
    return buf.getvalue()
