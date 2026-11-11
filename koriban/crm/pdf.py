"""Generación de PDFs de Koriban con ReportLab (Python puro, sin Django)."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .catalogos import MANTENIMIENTO_INCLUYE, SIGUIENTES_PASOS

TINTA = colors.HexColor("#10213A")
CORAL = colors.HexColor("#FF5B3A")
MENTA = colors.HexColor("#1FB89A")
ARENA = colors.HexColor("#F6F3EE")
GRIS = colors.HexColor("#5B6576")
LINEA = colors.HexColor("#E2DDD4")

ANCHO, ALTO = letter
MARGEN = 18 * mm


def moneda(valor):
    return "${:,.2f}".format(float(valor))


def dibujar_logo(c, x, y, tam=12 * mm):
    """Isotipo de Koriban: una 'K' formada por dos trazos que se unen en un nodo
    (el sitio web y el CRM conectados)."""
    c.saveState()
    c.setFillColor(TINTA)
    c.roundRect(x, y, tam, tam, tam * 0.22, stroke=0, fill=1)
    c.setStrokeColor(colors.white)
    c.setLineWidth(tam * 0.11)
    c.setLineCap(1)
    izq = x + tam * 0.32
    nodo_x, nodo_y = x + tam * 0.48, y + tam * 0.5
    c.line(izq, y + tam * 0.22, izq, y + tam * 0.78)
    c.line(nodo_x, nodo_y, x + tam * 0.72, y + tam * 0.78)
    c.line(nodo_x, nodo_y, x + tam * 0.72, y + tam * 0.22)
    c.setFillColor(CORAL)
    c.circle(nodo_x, nodo_y, tam * 0.1, stroke=0, fill=1)
    c.restoreState()


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], fontName="Helvetica-Bold",
                                 fontSize=20, leading=24, textColor=TINTA, alignment=0, spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontSize=10, textColor=GRIS, leading=14),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12.5,
                             textColor=TINTA, spaceBefore=10, spaceAfter=6),
        "normal": ParagraphStyle("normal", parent=base["Normal"], fontSize=9.5, leading=13.5, textColor=TINTA),
        "chico": ParagraphStyle("chico", parent=base["Normal"], fontSize=8.5, leading=12, textColor=GRIS),
        "derecha": ParagraphStyle("derecha", parent=base["Normal"], fontSize=9.5, leading=13,
                                  textColor=TINTA, alignment=TA_RIGHT),
        "vineta": ParagraphStyle("vineta", parent=base["Normal"], fontSize=9.5, leading=13.5,
                                 textColor=TINTA, leftIndent=10, bulletIndent=0),
    }


def _encabezado_y_pie(contacto, folio):
    def dibujar(c, doc):
        c.saveState()
        # Banda superior
        c.setFillColor(ARENA)
        c.rect(0, ALTO - 26 * mm, ANCHO, 26 * mm, stroke=0, fill=1)
        c.setFillColor(CORAL)
        c.rect(0, ALTO - 26 * mm, ANCHO, 1.2 * mm, stroke=0, fill=1)
        dibujar_logo(c, MARGEN, ALTO - 20 * mm, 12 * mm)
        c.setFillColor(TINTA)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(MARGEN + 15 * mm, ALTO - 13.5 * mm, "Koriban")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(GRIS)
        c.drawString(MARGEN + 15 * mm, ALTO - 18 * mm, "Soluciones digitales · Sitios web + CRM")
        if folio:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(TINTA)
            c.drawRightString(ANCHO - MARGEN, ALTO - 13.5 * mm, f"Folio {folio}")
        # Pie
        c.setStrokeColor(LINEA)
        c.line(MARGEN, 15 * mm, ANCHO - MARGEN, 15 * mm)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GRIS)
        c.drawString(MARGEN, 10 * mm,
                     f"{contacto.get('email', '')}  ·  Tel. {contacto.get('telefono', '')}  ·  "
                     f"{contacto.get('zona', '')}")
        c.drawRightString(ANCHO - MARGEN, 10 * mm, f"Página {doc.page}")
        c.restoreState()
    return dibujar


def _tabla(data, anchos, encabezado=True, zebra=True):
    t = Table(data, colWidths=anchos)
    estilo = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), TINTA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINEA),
    ]
    if encabezado:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), TINTA),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ]
    if zebra:
        for i in range(1 if encabezado else 0, len(data)):
            if i % 2 == 0:
                estilo.append(("BACKGROUND", (0, i), (-1, i), ARENA))
    t.setStyle(TableStyle(estilo))
    return t


def generar_pdf_cotizacion(info):
    """info = {folio, fecha, vence, cliente:{...}, resultado:{...}, vendedor, contacto:{...}}"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, leftMargin=MARGEN, rightMargin=MARGEN,
        topMargin=34 * mm, bottomMargin=22 * mm,
        title=f"Propuesta Koriban {info['folio']}", author="Koriban",
    )
    e = _estilos()
    r = info["resultado"]
    # Los datos capturados por el usuario se escapan para no romper el marcado de ReportLab
    cli = {k: escape(str(v or "")) for k, v in info["cliente"].items()}
    vendedor = escape(info.get("vendedor") or "el equipo Koriban")
    ancho_util = ANCHO - 2 * MARGEN
    h = []

    h.append(Paragraph("Propuesta de solución digital", e["titulo"]))
    h.append(Paragraph(
        f"Preparada para <b>{cli['nombre']}</b>"
        + (f" · {cli['empresa']}" if cli.get("empresa") else ""),
        e["sub"]))
    h.append(Spacer(1, 8))

    datos = [
        [Paragraph("<b>Fecha</b>", e["chico"]), Paragraph(info["fecha"], e["normal"]),
         Paragraph("<b>Vigencia</b>", e["chico"]),
         Paragraph(f"{r['vigencia_dias']} días (hasta {info['vence']})", e["normal"])],
        [Paragraph("<b>Giro</b>", e["chico"]), Paragraph(cli["giro"], e["normal"]),
         Paragraph("<b>Zona</b>", e["chico"]), Paragraph(cli.get("alcaldia") or "—", e["normal"])],
        [Paragraph("<b>Correo</b>", e["chico"]), Paragraph(cli["email"], e["normal"]),
         Paragraph("<b>Teléfono</b>", e["chico"]), Paragraph(cli.get("telefono") or "—", e["normal"])],
    ]
    h.append(_tabla(datos, [22 * mm, ancho_util / 2 - 22 * mm, 22 * mm, ancho_util / 2 - 22 * mm],
                    encabezado=False, zebra=False))

    # Paquete recomendado
    h.append(Paragraph("Paquete recomendado", e["h2"]))
    caja = Table([[
        Paragraph(f"<font size=14 color='#FF5B3A'><b>{r['paquete_nombre']}</b></font><br/>"
                  f"<font size=8.5 color='#5B6576'>Tiempo estimado de entrega: {r['semanas']} · "
                  f"Diagnóstico: {r['puntaje']} puntos</font>", e["normal"]),
    ]], colWidths=[ancho_util])
    caja.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ARENA),
        ("LINEBEFORE", (0, 0), (0, -1), 3, CORAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    h.append(caja)
    h.append(Spacer(1, 6))
    h.append(Paragraph("<b>Incluye:</b>", e["normal"]))
    for item in r["incluye"]:
        h.append(Paragraph(item, e["vineta"], bulletText="•"))
    h.append(Spacer(1, 4))
    h.append(Paragraph(f"<b>Sugerido para tu giro ({cli['giro']}):</b>", e["normal"]))
    for item in r["modulos_giro"]:
        h.append(Paragraph(item, e["vineta"], bulletText="•"))

    # Inversión
    precios = [
        ["Concepto", "Importe"],
        [f"Implementación — {r['paquete_nombre']}", moneda(r["precio"])],
        [f"IVA ({r['iva_pct']}%)", moneda(r["iva"])],
        ["Total del proyecto", moneda(r["total"])],
        [f"Anticipo al firmar ({r['anticipo_pct']}%)", moneda(r["anticipo"])],
        ["Mantenimiento mensual (opcional, + IVA)", moneda(r["mantenimiento"]) + " / mes"],
    ]
    t = _tabla(precios, [ancho_util * 0.68, ancho_util * 0.32])
    t.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONT", (0, 3), (-1, 3), "Helvetica-Bold", 10),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FFE7E1")),
    ]))
    h.append(KeepTogether([Paragraph("Inversión", e["h2"]), t]))
    h.append(Spacer(1, 4))
    h.append(Paragraph(
        f"El mantenimiento incluye: {MANTENIMIENTO_INCLUYE.lower()}. "
        f"Con IVA: {moneda(r['mantenimiento_con_iva'])} al mes.", e["chico"]))
    h.append(Paragraph(
        f"Forma de pago: {r['anticipo_pct']}% de anticipo a la firma del contrato y el resto "
        "a la entrega del proyecto. Precios en pesos mexicanos.", e["chico"]))

    if r.get("observaciones"):
        h.append(Paragraph("Observaciones", e["h2"]))
        for o in r["observaciones"]:
            h.append(Paragraph(o, e["vineta"], bulletText="•"))

    # Diagnóstico
    diag = [["Factor evaluado", "Puntos"]] + [[d["concepto"], str(d["puntos"])] for d in r["desglose"]]
    diag.append(["Total", str(r["puntaje"])])
    td = _tabla(diag, [ancho_util * 0.8, ancho_util * 0.2])
    td.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"),
                            ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9)]))
    h.append(KeepTogether([Paragraph("Cómo llegamos a esta propuesta", e["h2"]), td]))

    # Siguientes pasos
    pasos = [["#", "Siguiente paso", "En qué consiste"]]
    for i, (paso, desc) in enumerate(SIGUIENTES_PASOS, 1):
        pasos.append([str(i), Paragraph(f"<b>{paso}</b>", e["normal"]), Paragraph(desc, e["normal"])])
    tp = _tabla(pasos, [10 * mm, 42 * mm, ancho_util - 52 * mm])
    tp.setStyle(TableStyle([("ALIGN", (0, 0), (0, -1), "CENTER"),
                            ("TEXTCOLOR", (0, 1), (0, -1), CORAL),
                            ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 10)]))
    h.append(KeepTogether([Paragraph("Siguientes pasos", e["h2"]), tp]))

    h.append(Spacer(1, 12))
    contacto = info["contacto"]
    h.append(Paragraph(
        f"¿Listo para empezar? Responde este correo o escríbenos por WhatsApp al "
        f"<b>{contacto.get('telefono', '')}</b>. Tu asesor asignado es <b>{vendedor}</b>.",
        e["normal"]))

    pagina = _encabezado_y_pie(contacto, info["folio"])
    doc.build(h, onFirstPage=pagina, onLaterPages=pagina)
    return buffer.getvalue()


def generar_pdf_simple(titulo, subtitulo, parrafos, contacto, folio=""):
    """PDF genérico con la identidad de Koriban (contratos de ejemplo, minutas, etc.)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=MARGEN, rightMargin=MARGEN,
                            topMargin=34 * mm, bottomMargin=22 * mm, title=titulo, author="Koriban")
    e = _estilos()
    h = [Paragraph(escape(titulo), e["titulo"]), Paragraph(escape(subtitulo), e["sub"]), Spacer(1, 10)]
    for p in parrafos:
        h.append(Paragraph(p, e["normal"]))
        h.append(Spacer(1, 6))
    pagina = _encabezado_y_pie(contacto, folio)
    doc.build(h, onFirstPage=pagina, onLaterPages=pagina)
    return buffer.getvalue()
