"""
PDF-Rechnungsgenerierung mit reportlab.
"""

import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

RECHNUNGEN_DIR = Path(__file__).parent / "rechnungen"
RECHNUNGEN_DIR.mkdir(exist_ok=True)


def _format_betrag(betrag):
    return f"{betrag:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")


def rechnung_als_pdf(rechnungsnummer, firma, kunde, kunde_adresse, datum,
                     leistungszeitraum_von, leistungszeitraum_bis,
                     positionen, gesamtbetrag):
    """
    Erstellt eine PDF-Rechnung.

    positionen: Liste von Dicts mit keys: beschreibung, stunden, stundensatz, betrag
    firma: Dict mit Firmendaten
    """
    pdf_path = RECHNUNGEN_DIR / f"{rechnungsnummer}.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                            leftMargin=25*mm, rightMargin=25*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="RightAlign", parent=styles["Normal"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="SmallGray", parent=styles["Normal"],
                              fontSize=8, textColor=colors.gray))
    styles.add(ParagraphStyle(name="Header", parent=styles["Normal"],
                              fontSize=18, spaceAfter=5))
    styles.add(ParagraphStyle(name="SubHeader", parent=styles["Normal"],
                              fontSize=10, textColor=colors.gray, spaceAfter=15))

    elements = []

    # Firmenname als Header
    elements.append(Paragraph(firma.get("firma_name", "Firma"), styles["Header"]))
    firma_zeile = " | ".join(filter(None, [
        firma.get("inhaber", ""),
        f'{firma.get("strasse", "")}, {firma.get("plz", "")} {firma.get("ort", "")}',
        firma.get("telefon", ""),
        firma.get("email", ""),
    ]))
    elements.append(Paragraph(firma_zeile, styles["SmallGray"]))
    elements.append(Spacer(1, 15*mm))

    # Empfänger
    elements.append(Paragraph(kunde, styles["Normal"]))
    for zeile in kunde_adresse.split("\n"):
        if zeile.strip():
            elements.append(Paragraph(zeile.strip(), styles["Normal"]))
    elements.append(Spacer(1, 10*mm))

    # Rechnungsdetails
    elements.append(Paragraph(f"<b>Rechnung {rechnungsnummer}</b>", styles["Heading2"]))
    details = [
        ["Rechnungsdatum:", datum],
        ["Leistungszeitraum:", f"{leistungszeitraum_von} bis {leistungszeitraum_bis}"],
    ]
    if firma.get("steuernummer"):
        details.append(["Steuernummer:", firma["steuernummer"]])
    if firma.get("ust_id"):
        details.append(["USt-IdNr.:", firma["ust_id"]])

    detail_table = Table(details, colWidths=[45*mm, 100*mm])
    detail_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.gray),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 8*mm))

    # Positionstabelle
    header = ["Pos.", "Beschreibung", "Stunden", "Satz", "Betrag"]
    table_data = [header]
    for i, pos in enumerate(positionen, 1):
        table_data.append([
            str(i),
            pos["beschreibung"],
            f'{pos["stunden"]:.2f}',
            _format_betrag(pos["stundensatz"]),
            _format_betrag(pos["betrag"]),
        ])

    # Summenzeile
    table_data.append(["", "", "", "Gesamt:", _format_betrag(gesamtbetrag)])

    col_widths = [12*mm, 72*mm, 22*mm, 28*mm, 28*mm]
    pos_table = Table(table_data, colWidths=col_widths)
    pos_table.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        # Grid
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#2c3e50")),
        ("LINEBELOW", (0, -2), (-1, -2), 0.5, colors.lightgrey),
        # Summenzeile
        ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (3, -1), (-1, -1), 1, colors.HexColor("#2c3e50")),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
    ]))
    elements.append(pos_table)
    elements.append(Spacer(1, 15*mm))

    # Hinweis Kleinunternehmer (Platzhalter)
    elements.append(Paragraph(
        "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet (Kleinunternehmerregelung). "
        "Bitte überweisen Sie den Gesamtbetrag innerhalb von 14 Tagen.",
        ParagraphStyle(name="Hinweis", parent=styles["Normal"], fontSize=8,
                       textColor=colors.gray, spaceAfter=8)
    ))

    # Bankverbindung
    bank_info = f"<b>Bankverbindung:</b> {firma.get('bank_name', '')} | " \
                f"IBAN: {firma.get('iban', '')} | BIC: {firma.get('bic', '')}"
    elements.append(Paragraph(bank_info, ParagraphStyle(
        name="Bank", parent=styles["Normal"], fontSize=8, textColor=colors.gray)))

    doc.build(elements)
    return pdf_path
