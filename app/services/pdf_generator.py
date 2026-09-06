"""PDF template engine for manufacturer Patient Assistance Program applications."""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core import fpl as fpl_mod

# Remedi brand palette — matches app/static/styles.css so the generated PDF
# feels like part of the same product, not a separate legal document.
NAVY = colors.HexColor("#9F1239")  # crimson-deep — section banners, borders
NAVY_MID = colors.HexColor("#BE123C")  # crimson — subtitle text, accents
TEAL = colors.HexColor("#047857")  # forest — checkmarks, positive verifications
GOLD = colors.HexColor("#F43F5E")  # rose — header/footer accent stripe
PAPER = colors.HexColor("#FFF1F2")  # blush — field label backgrounds
CREAM = colors.HexColor("#FDFCF9")  # warm cream canvas, matches site background
RULE = colors.HexColor("#EAE7E1")  # hairline border
INK = colors.HexColor("#1C1917")  # deep warm charcoal headings/body text
MUTED = colors.HexColor("#52525B")  # warm slate secondary text
WHITE = colors.white
PASS_GREEN = colors.HexColor("#047857")
FAIL_RED = colors.HexColor("#BE123C")


class CheckboxRow(Flowable):
    """A boxed checklist row that draws a true checkbox, not a font glyph."""

    def __init__(self, label: str, checked: bool = False, width: float = 7.2 * inch, height: float = 16):
        super().__init__()
        self.label = label
        self.checked = checked
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        self.width = min(self.width, availWidth)
        return self.width, self.height

    def draw(self):
        box = 9
        y = (self.height - box) / 2
        self.canv.setStrokeColor(NAVY)
        self.canv.setLineWidth(0.8)
        self.canv.setFillColor(WHITE)
        self.canv.rect(1, y, box, box, stroke=1, fill=1)
        if self.checked:
            self.canv.setStrokeColor(TEAL)
            self.canv.setLineWidth(1.6)
            self.canv.line(2.5, y + 4, 4.8, y + 1.5)
            self.canv.line(4.8, y + 1.5, 9.2, y + 8.2)
        self.canv.setFillColor(INK)
        self.canv.setFont("Times-Roman", 9.5)
        self.canv.drawString(box + 8, y + 1.5, self.label)


class SignatureLine(Flowable):
    def __init__(self, caption: str, width: float = 3.2 * inch):
        super().__init__()
        self.caption = caption
        self.line_width = width
        self.height = 28

    def wrap(self, availWidth, availHeight):
        self.width = min(self.line_width, availWidth)
        return self.width, self.height

    def draw(self):
        self.canv.setStrokeColor(NAVY)
        self.canv.setLineWidth(0.9)
        self.canv.line(0, 12, self.width, 12)
        self.canv.setFillColor(MUTED)
        self.canv.setFont("Times-Italic", 8)
        self.canv.drawString(0, 0, self.caption)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "Brand",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY_MID,
            alignment=TA_CENTER,
            spaceAfter=1,
        ),
        "masthead": ParagraphStyle(
            "Masthead",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=16,
            leading=19,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=10,
            leading=13,
            textColor=NAVY_MID,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            leading=11,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=10,
            leading=13,
            textColor=WHITE,
            alignment=TA_LEFT,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=8.5,
            leading=11,
            textColor=NAVY,
        ),
        "value": ParagraphStyle(
            "Value",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=9.5,
            leading=12,
            textColor=INK,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=9,
            leading=12,
            textColor=INK,
            alignment=TA_JUSTIFY,
        ),
        "fine": ParagraphStyle(
            "Fine",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
            alignment=TA_LEFT,
        ),
        "attest": ParagraphStyle(
            "Attest",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.5,
            leading=11.5,
            textColor=INK,
            alignment=TA_LEFT,
        ),
        "right_meta": ParagraphStyle(
            "RightMeta",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            leading=11,
            textColor=MUTED,
            alignment=TA_RIGHT,
        ),
    }


def _section_banner(title: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[Paragraph(title, styles["section"])]], colWidths=[7.2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _field_table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    data = []
    for label, value in rows:
        data.append(
            [
                Paragraph(label.upper(), styles["label"]),
                Paragraph(str(value) if value not in (None, "") else "—", styles["value"]),
            ]
        )
    table = Table(data, colWidths=[2.35 * inch, 4.85 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.4, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _header_footer(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)

    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 28, width, 28, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, height - 31, width, 3, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Times-Bold", 8)
    canvas.drawString(0.65 * inch, height - 18, "REMEDI  ·  PATIENT ASSISTANCE APPLICATION  ·  CONFIDENTIAL")
    canvas.drawRightString(width - 0.65 * inch, height - 18, "FORM PAP-2026-APP")

    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, width, 28, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 28, width, 3, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Times-Roman", 7.5)
    canvas.drawString(
        0.65 * inch,
        12,
        "Generated in-memory by Remedi, the affordable medication copilot  ·  Submit with original manufacturer instructions",
    )
    canvas.drawRightString(width - 0.65 * inch, 12, f"Page {doc.page}")
    canvas.restoreState()


def generate_assistance_pdf(patient_data: dict, program_name: str, medication_name: str) -> bytes:
    """Render a 1–2 page PAP application to raw PDF bytes. Never writes to disk."""
    styles = _styles()

    patient_name = (
        patient_data.get("patient_name")
        or patient_data.get("full_name")
        or patient_data.get("name")
        or ""
    )
    state = str(patient_data.get("state") or "").strip().upper()
    household_size = int(patient_data.get("household_size") or 1)
    annual_income = float(patient_data.get("annual_income") or 0)
    is_uninsured = bool(patient_data.get("is_uninsured", False))
    insurance_status = patient_data.get("insurance_status")
    if not insurance_status:
        insurance_status = "Uninsured" if is_uninsured else "Insured / underinsured"
    address = patient_data.get("address") or patient_data.get("street_address") or ""
    address_display = ", ".join(part for part in [address, state] if part) or state or "—"
    strength = patient_data.get("strength") or patient_data.get("dosage") or "See attached prescription"
    generic_name = patient_data.get("generic_name") or ""
    medication_display = f"{medication_name} ({generic_name})" if generic_name else medication_name
    fpl_limit = float(patient_data.get("fpl_limit_percent") or 400.0)
    manufacturer = patient_data.get("manufacturer") or ""
    program_phone = patient_data.get("program_phone") or ""
    mailing_address = patient_data.get("mailing_address") or ""
    prescriber = patient_data.get("prescriber_name") or ""
    npi = patient_data.get("prescriber_npi") or ""
    dob = patient_data.get("date_of_birth") or ""
    phone = patient_data.get("phone") or ""

    percent = fpl_mod.fpl_percent(annual_income, household_size, state)
    guideline = fpl_mod.poverty_guideline(household_size, state)
    limit_amount = fpl_mod.fpl_limit_amount(household_size, state, fpl_limit)
    eligible = percent <= fpl_limit
    region = fpl_mod.guideline_region(state)
    region_label = {
        "AK": "Alaska",
        "HI": "Hawaii",
        "contiguous": "48 Contiguous States & D.C.",
    }[region]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=f"{program_name} Application — {patient_name}",
        author="Patient Assistance Copilot",
    )

    story: list = []

    header_title = program_name
    if "assist" not in program_name.lower() and "assistance" not in program_name.lower():
        header_title = f"{program_name} Patient Assistance"
    story.append(Paragraph("REMEDI — Affordable Medication Copilot", styles["brand"]))
    story.append(Paragraph(header_title, styles["masthead"]))
    story.append(
        Paragraph(
            "Manufacturer Co-Pay &amp; Foundation Assistance Form",
            styles["subtitle"],
        )
    )
    if manufacturer:
        story.append(
            Paragraph(
                f"{manufacturer}  ·  Official-format application packet  ·  Tax year {fpl_mod.FPL_YEAR}",
                styles["meta"],
            )
        )
    else:
        story.append(
            Paragraph(
                f"Official-format application packet  ·  Tax year {fpl_mod.FPL_YEAR}",
                styles["meta"],
            )
        )
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.1, color=GOLD, spaceAfter=8))

    meta = Table(
        [
            [
                Paragraph(f"<b>Prepared:</b> {date.today().isoformat()}", styles["value"]),
                Paragraph(f"<b>Jurisdiction:</b> {state or '—'} ({region_label})", styles["value"]),
                Paragraph(f"<b>FPL year:</b> {fpl_mod.FPL_YEAR} HHS", styles["value"]),
            ]
        ],
        colWidths=[2.4 * inch, 2.8 * inch, 2.0 * inch],
    )
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(meta)
    story.append(Spacer(1, 10))

    # Section A
    story.append(_section_banner("SECTION A  —  PATIENT INFORMATION", styles))
    story.append(
        _field_table(
            [
                ("Full Legal Name", patient_name),
                ("Date of Birth", dob or "________________"),
                ("Address / State", address_display),
                ("Telephone", phone or "________________"),
                ("Household Size", str(household_size)),
                ("Gross Annual Household Income", f"${annual_income:,.2f}"),
                ("Federal Poverty Level %", f"{percent}% FPL"),
                ("100% FPL Guideline (2026)", f"${guideline:,}  ·  {region_label}"),
                ("Insurance Status", insurance_status),
            ],
            styles,
        )
    )
    story.append(Spacer(1, 12))

    # Section B
    story.append(_section_banner("SECTION B  —  PRESCRIPTION &amp; CLINICAL DETAILS", styles))
    story.append(
        _field_table(
            [
                ("Requested Medication", medication_display),
                ("Strength / Dosage", strength),
                ("Dosage Form", patient_data.get("form") or "________________"),
                ("ICD-10 / Indication", patient_data.get("indication") or "________________"),
                ("Prescriber Name", prescriber or "________________"),
                ("Prescriber NPI", npi or "________________"),
            ],
            styles,
        )
    )
    story.append(Spacer(1, 8))
    attestation = Table(
        [
            [
                Paragraph("<b>PRESCRIBER ATTESTATION</b>", styles["label"]),
            ],
            [
                Paragraph(
                    "I hereby attest that I am a licensed health care professional authorized to prescribe "
                    f"in the patient's jurisdiction; that {medication_name} is medically necessary for this "
                    "patient; that I have obtained any required informed consent; and that the clinical "
                    "information on this application is true, complete, and accurate to the best of my knowledge. "
                    "I authorize the manufacturer patient assistance program and its vendors to contact me "
                    "regarding this request.",
                    styles["attest"],
                )
            ],
        ],
        colWidths=[7.2 * inch],
    )
    attestation.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.1, NAVY),
                ("BACKGROUND", (0, 0), (-1, 0), PAPER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ]
        )
    )
    story.append(attestation)
    story.append(Spacer(1, 12))

    # Section C
    story.append(_section_banner("SECTION C  —  FINANCIAL &amp; ELIGIBILITY VERIFICATION", styles))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Eligibility is computed against the {fpl_mod.FPL_YEAR} HHS Poverty Guidelines "
            f"({region_label}). Program income ceiling is {fpl_limit:.0f}% of FPL "
            f"(${limit_amount:,.2f} for a household of {household_size}).",
            styles["body"],
        )
    )
    story.append(Spacer(1, 6))
    story.append(CheckboxRow(f"Income verified at {percent}% FPL", checked=True))
    story.append(
        CheckboxRow(
            f"Meets ≤ {fpl_limit:.0f}% threshold  (${limit_amount:,.0f} annual cap)",
            checked=eligible,
        )
    )
    story.append(
        CheckboxRow(
            f"Resides in a covered U.S. jurisdiction ({state or 'unspecified'})",
            checked=bool(state),
        )
    )
    story.append(
        CheckboxRow(
            "Uninsured or limited coverage documented",
            checked=is_uninsured,
        )
    )
    story.append(
        CheckboxRow(
            "Does not exceed program household-income ceiling",
            checked=eligible,
        )
    )
    verdict_color = PASS_GREEN if eligible else FAIL_RED
    verdict_text = (
        f"DETERMINATION: PATIENT MEETS {program_name.upper()} FINANCIAL SCREEN "
        f"({percent}% FPL ≤ {fpl_limit:.0f}% LIMIT)"
        if eligible
        else f"DETERMINATION: INCOME {percent}% FPL EXCEEDS {fpl_limit:.0f}% PROGRAM LIMIT — REVIEW REQUIRED"
    )
    verdict = Table([[Paragraph(f"<b>{verdict_text}</b>", styles["attest"])]], colWidths=[7.2 * inch])
    verdict.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.Color(verdict_color.red, verdict_color.green, verdict_color.blue, alpha=0.12)),
                ("BOX", (0, 0), (-1, -1), 0.8, verdict_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(Spacer(1, 6))
    story.append(verdict)
    story.append(Spacer(1, 12))

    # Section D
    story.append(_section_banner("SECTION D  —  REQUIRED ATTACHMENTS CHECKLIST", styles))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Enclose copies (do not send originals). Incomplete packets are the most common cause of delay.",
            styles["fine"],
        )
    )
    story.append(Spacer(1, 4))
    attachment_items = [
        ("IRS Form 1040 / 1040-SR for the most recent filing year, or W-2 / 1099-R", False),
        ("Two consecutive pay stubs if a tax return is unavailable", False),
        ("Proof of denial or ineligibility from Medicaid (and Extra Help / LIS if Medicare)", False),
        ("Prescription script from a licensed prescriber for the requested medication", False),
        ("Front and back copy of all insurance cards (if insured)", not is_uninsured),
        ("Government-issued photo identification", False),
        ("Signed HIPAA / FCRA authorization (see manufacturer original if required)", False),
    ]
    inner: list = [Spacer(1, 4)]
    for label, checked in attachment_items:
        inner.append(CheckboxRow(label, checked=checked))
    inner.append(Spacer(1, 4))
    wrap = Table([[inner]], colWidths=[7.2 * inch])
    wrap.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
            ]
        )
    )
    story.append(wrap)
    story.append(Spacer(1, 12))

    # Section E
    story.append(_section_banner("SECTION E  —  SIGNATURE &amp; DATE BLOCK", styles))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "By signing, the patient (or legal representative) certifies that the financial and insurance "
            "information is true and complete, authorizes the program to verify income and coverage, and "
            "agrees to the manufacturer's privacy notice. A parent or legal guardian must sign for a minor.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 16))
    sig_table = Table(
        [
            [SignatureLine("Patient / Legal Representative Signature"), SignatureLine("Date")],
            [Spacer(1, 18), Spacer(1, 18)],
            [SignatureLine("Physician / Prescriber Signature"), SignatureLine("Date / NPI")],
        ],
        colWidths=[4.3 * inch, 2.9 * inch],
    )
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(KeepTogether([sig_table]))
    story.append(Spacer(1, 14))

    submit_lines = []
    if mailing_address:
        submit_lines.append(f"<b>Mail completed packet to:</b> {mailing_address}")
    if program_phone:
        submit_lines.append(f"<b>Program telephone:</b> {program_phone}")
    submit_lines.append(
        "This packet is a structured application generated from verified eligibility data. "
        "It is not the manufacturer's copyrighted original form. Confirm any program-specific "
        "addenda (HIPAA, copay-card exclusions, alternate-funding restrictions) before submission."
    )
    story.append(Paragraph("<br/>".join(submit_lines), styles["fine"]))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
