import io
import os
from flask import render_template, make_response
from flask_babel import gettext as _
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


_FONTS_REGISTERED = False


def _register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    italic_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"
    bolditalic_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"
    mono_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Oblique", italic_path))
        pdfmetrics.registerFont(TTFont("DejaVuSans-BoldOblique", bolditalic_path))
        pdfmetrics.registerFont(TTFont("DejaVuSansMono", mono_path))

        pdfmetrics.registerFontFamily(
            "DejaVuSans",
            normal="DejaVuSans",
            bold="DejaVuSans-Bold",
            italic="DejaVuSans-Oblique",
            boldItalic="DejaVuSans-BoldOblique",
        )
        _FONTS_REGISTERED = True


def render_pdf(template, **context):
    _register_fonts()
    html = render_template(template, **context)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if pdf.err:
        return None
    response = make_response(result.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f"attachment; filename={context.get('filename', 'report')}.pdf"
    )
    return response
