"""Generate Cyrillic PDFs in memory, without native Pango or network access."""

import base64
import binascii
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
from threading import Lock
from typing import Optional
from xml.sax.saxutils import escape

from PIL import Image as PillowImage, ImageOps, UnidentifiedImageError
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer


STUDY_TYPE_LABELS = {
    "retinal_scan": "Сканирование сетчатки",
    "optic_nerve": "Анализ зрительного нерва",
    "macular_analysis": "Анализ макулярной области",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_ANALYSIS_CHARS = 100_000
MAX_PDF_BYTES = 3 * 1024 * 1024
PDF_PREVIEW_MAX_DIMENSION = 1600
_RASTER_FORMATS = {
    "image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP",
    "image/gif": "GIF", "image/bmp": "BMP",
}
_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_FONT_LOCK = Lock()
_FONT_REGULAR = "MedScanNotoSans"
_FONT_BOLD = "MedScanNotoSans-Bold"


def _register_fonts() -> None:
    """Only load bundled, trusted font files; never user-supplied paths."""
    with _FONT_LOCK:
        if _FONT_REGULAR not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(_FONT_REGULAR, str(_FONT_DIR / "NotoSans-Regular.ttf")))
            pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(_FONT_DIR / "NotoSans-Bold.ttf")))
            pdfmetrics.registerFontFamily(
                _FONT_REGULAR, normal=_FONT_REGULAR, bold=_FONT_BOLD,
                italic=_FONT_REGULAR, boldItalic=_FONT_BOLD,
            )


def _plain_text(value: str) -> str:
    """Remove XML-forbidden controls, preserving readable line breaks."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]", "\ufffd", value)


def _escaped_text(value: str) -> str:
    # Paragraph supports XML-like markup, including images and links. Escape ALL
    # user text so those features cannot be used for file/network access.
    return escape(_plain_text(value))


def _decode_raster_image(image_url: str) -> BytesIO:
    """Accept bounded raster data URLs only, and normalize them in memory."""
    if len(image_url) > ((MAX_IMAGE_BYTES + 2) // 3) * 4 + 64:
        raise ValueError("PDF image exceeds the 10 MB limit")
    match = re.fullmatch(r"data:(image/[a-z]+);base64,([A-Za-z0-9+/=]+)", image_url)
    if not match or match.group(1) not in _RASTER_FORMATS:
        raise ValueError("PDF images must be base64 PNG, JPEG, WebP, GIF or BMP data URLs")
    try:
        content = base64.b64decode(match.group(2), validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("Invalid base64 PDF image") from error
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Invalid PDF image size")
    try:
        with PillowImage.open(BytesIO(content)) as source:
            if source.format != _RASTER_FORMATS[match.group(1)]:
                raise ValueError("PDF image content does not match its MIME type")
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise ValueError("PDF image exceeds the 20 megapixel limit")
            # Apply EXIF rotation, then discard metadata and embedded payloads.
            # Animated uploads use their first frame as a printable still.
            normalized = ImageOps.exif_transpose(source).convert("RGBA")
            normalized.thumbnail(
                (PDF_PREVIEW_MAX_DIMENSION, PDF_PREVIEW_MAX_DIMENSION),
                resample=PillowImage.Resampling.LANCZOS,
            )
            # The downloadable PDF embeds a bounded viewing copy, not the
            # stored original. Flatten transparency onto white for JPEG.
            preview = PillowImage.new("RGB", normalized.size, "white")
            preview.paste(normalized, mask=normalized.getchannel("A"))
            result = BytesIO()
            preview.save(result, format="JPEG", quality=90, optimize=True)
            result.seek(0)
            return result
    except (UnidentifiedImageError, OSError, PillowImage.DecompressionBombError) as error:
        raise ValueError("Invalid raster PDF image") from error


def _page_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
    canvas.line(document.leftMargin, 1.65 * cm, A4[0] - document.rightMargin, 1.65 * cm)
    canvas.setFont(_FONT_REGULAR, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(document.leftMargin, 1.15 * cm, "МедСкан - требуется проверка специалистом")
    canvas.drawRightString(A4[0] - document.rightMargin, 1.15 * cm, f"Страница {document.page}")
    canvas.restoreState()


async def generate_pdf(
    title: str,
    study_type: str,
    created_at: datetime,
    analysis_result: str,
    image_url: Optional[str] = None,
) -> bytes:
    """Keep the study API stable; all document processing stays in memory.

    The existing plain-text protocol and its line/paragraph breaks are retained.
    HTML is rendered literally, not executed or fetched. No network, file URLs,
    external CSS, or operating-system fonts are used.
    """
    if len(title) > 1000 or len(study_type) > 200 or len(analysis_result) > MAX_ANALYSIS_CHARS:
        raise ValueError("Слишком большой текст PDF: название до 1000 символов, протокол до 100000 символов.")
    _register_fonts()
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=2.2 * cm,
        title=_plain_text(title), author="МедСкан", pageCompression=1,
    )
    base_style = ParagraphStyle(
        "Protocol", fontName=_FONT_REGULAR, fontSize=10.5, leading=16,
        textColor=colors.HexColor("#1e293b"), alignment=TA_LEFT,
        spaceAfter=6, splitLongWords=True, allowWidows=0, allowOrphans=0,
    )
    title_style = ParagraphStyle(
        "Title", parent=base_style, fontName=_FONT_BOLD,
        fontSize=20, leading=26, alignment=TA_CENTER,
        textColor=colors.HexColor("#2563eb"), spaceAfter=12,
    )
    metadata_style = ParagraphStyle(
        "Metadata", parent=base_style, alignment=TA_CENTER,
        textColor=colors.HexColor("#64748b"), fontSize=10, leading=15,
    )
    heading_style = ParagraphStyle(
        "Heading", parent=base_style, fontName=_FONT_BOLD,
        fontSize=14, leading=20, textColor=colors.HexColor("#2563eb"),
        spaceBefore=10, spaceAfter=10, keepWithNext=True,
    )
    caption_style = ParagraphStyle(
        "ImageCaption", parent=metadata_style, fontSize=8, leading=12,
        spaceBefore=6, spaceAfter=8,
    )
    study_type_label = STUDY_TYPE_LABELS.get(study_type, study_type)
    story = [
        Paragraph(_escaped_text(title), title_style),
        Paragraph(f"Тип исследования: {_escaped_text(study_type_label)}", metadata_style),
        Paragraph(f"Дата: {created_at.strftime('%d.%m.%Y')}", metadata_style),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=1.3, color=colors.HexColor("#2563eb")),
        Spacer(1, 10),
    ]
    if image_url:
        image_buffer = _decode_raster_image(image_url)
        image = Image(image_buffer)
        scale = min(document.width / image.imageWidth, 240 / image.imageHeight, 1)
        image.drawWidth = image.imageWidth * scale
        image.drawHeight = image.imageHeight * scale
        image.hAlign = "CENTER"
        story.extend([
            image,
            Paragraph(
                "Изображение в PDF - уменьшенная копия для просмотра. "
                "Оригинал доступен в исследовании.", caption_style,
            ),
            Spacer(1, 10),
        ])
    story.append(Paragraph("Результаты анализа", heading_style))
    # Legacy model output sometimes contains literal backslash-n characters.
    normalized_analysis = analysis_result.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized_analysis.split("\n"):
        if not line.strip():
            story.append(Spacer(1, 5))
            continue
        # Keep indentation, while letting long plain-text lines wrap naturally.
        indent = min(len(line) - len(line.lstrip(" \t")), 12)
        text = "&#160;" * indent + _escaped_text(line.lstrip(" \t"))
        story.append(Paragraph(text, base_style))
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    pdf_bytes = output.getvalue()
    # Base64 expands the API response by ~4/3. Keep it safely below Vercel's
    # 4.5 MB response limit, including the JSON envelope and filename.
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("PDF превышает лимит 3 МиБ. Сократите текст протокола и повторите экспорт.")
    return pdf_bytes
