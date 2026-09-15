from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
import cloudinary
import cloudinary.uploader
import os
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Image as RLImage
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable
from io import BytesIO
from app.config import BASE_DIR

pdfmetrics.registerFont(TTFont("Arabic", f"{BASE_DIR}/static/fonts/NotoSansArabic-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Arabic-Bold", f"{BASE_DIR}/static/fonts/NotoSansArabic-Bold.ttf"))



cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


ALLOWED_PFP_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PFP_SIZE = 5 * 1024 * 1024
MAX_PFP_PIXELS = 10_000_000


ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "application/pdf"
}
MAX_FILE_SIZE = 5 * 1024 * 1024

def is_material_valid(file: UploadFile):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        return False

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        return False
    if size == 0:
        return False

    return True

def upload_image(file: UploadFile, folder: str):
    result = cloudinary.uploader.upload(
        file.file,
        folder=f"{folder}",
        transformation=[
            {"width": 256, "height": 256, "crop": "fill"},
            {"quality": "auto"}
        ]
    )
    return result["public_id"]

def upload_file(file: UploadFile, folder: str):
    result = cloudinary.uploader.upload(
        file.file,
        folder=f"{folder}",
        transformation=[
            {"quality": "auto"}
        ]
    )
    return result["public_id"]

def generate_url(public_id, resource_type):
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type=f"{resource_type}",
    )
    return url

def delete_file(public_id: str, resource_type: str):
    cloudinary.uploader.destroy(public_id, resource_type=resource_type)

def is_valid_image(upload_file) -> bool:
    try:
        contents = upload_file.file.read()
        if not contents:
            return False
        if len(contents) > MAX_PFP_SIZE:
            return False
        if upload_file.content_type not in ALLOWED_PFP_MIME_TYPES:
            return False
        image = Image.open(BytesIO(contents))
        image.verify()
        image = Image.open(BytesIO(contents))
        width, height = image.size
        if width * height > MAX_PFP_PIXELS:
            return False
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            return False
        return True

    except (UnidentifiedImageError, OSError, ValueError):
        return False
    finally:
        upload_file.file.seek(0)

def ar(text) -> str:
    if text is None:
        return ""
    text = str(text)
    if not text:
        return text
    return get_display(arabic_reshaper.reshape(text))

class VerticalText(Flowable):
    """Draws Arabic text rotated 90° (reading top-to-bottom), wrapping within a given box."""
    def __init__(self, text, font_name, font_size, width, height, min_font_size=6):
        Flowable.__init__(self)
        self.text = text
        self.font_name = font_name
        self.font_size = font_size
        self.min_font_size = min_font_size
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def _wrap_text(self):
        padding = 6  # a little breathing room top/bottom
        available_length = max(self.height - padding, 0)

        lines = []
        current_line = ""
        for word in self.text.split():
            candidate = f"{current_line} {word}".strip()
            if current_line and stringWidth(candidate, self.font_name, self.font_size) > available_length:
                lines.append(current_line)
                current_line = ""

            while stringWidth(word, self.font_name, self.font_size) > available_length:
                split_at = len(word)
                while split_at > 1 and stringWidth(word[:split_at], self.font_name, self.font_size) > available_length:
                    split_at -= 1
                lines.append(word[:split_at])
                word = word[split_at:]

            current_line = word if not current_line else f"{current_line} {word}"

        if current_line:
            lines.append(current_line)

        return lines or [""]

    def draw(self):
        canvas = self.canv
        lines = self._wrap_text()
        line_spacing = self.font_size * 1.15
        canvas.saveState()
        canvas.setFillColor(colors.black)
        canvas.setFont(self.font_name, self.font_size)
        canvas.translate(self.width / 2, self.height / 2)
        canvas.rotate(90)
        first_line_offset = (len(lines) - 1) * line_spacing / 2
        for index, line in enumerate(lines):
            offset = first_line_offset - index * line_spacing
            canvas.drawCentredString(0, offset - self.font_size / 3, line)
        canvas.restoreState()


def generate_extract_pdf(extract, categories, items_by_cat) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # --- Arabic paragraph styles ---
    title_style = ParagraphStyle(
        "title_ar", parent=styles["Title"], fontName="Arabic-Bold", alignment=TA_RIGHT
    )
    normal_style = ParagraphStyle(
        "normal_ar", parent=styles["Normal"], fontName="Arabic", fontSize=11,
        leading=15, alignment=TA_RIGHT, wordWrap="RTL"
    )
    cell_style = ParagraphStyle(
        "cell_ar", parent=styles["Normal"], fontName="Arabic", fontSize=9,
        leading=13, alignment=TA_RIGHT, wordWrap="RTL"
    )
    header_style = ParagraphStyle(
        "cell_header_ar", parent=cell_style, fontName="Arabic-Bold", textColor=colors.white
    )
    totals_label_style = ParagraphStyle(
        "totals_label_ar", parent=cell_style, fontName="Arabic-Bold"
    )
    totals_value_style = ParagraphStyle(
        "totals_value_ar", parent=cell_style, fontName="Helvetica-Bold", alignment=TA_LEFT
    )

    logo_path = os.path.join(BASE_DIR, "static", "pdf_logo.png")
    logo = RLImage(logo_path, width=6 * cm, height=2 * cm)

    header_text = Paragraph(f"{extract.id} {ar('مستخلص')}", title_style)

    header_table = Table(
        [[logo, header_text]],
        colWidths=[4 * cm, 12 * cm]
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # vertically centers logo + text relative to each other
        ("ALIGN", (0, 0), (0, 0), "CENTER"),  # centers the logo within its cell
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),  # keeps Arabic text right-aligned within its cell
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"{ar(extract.project_name)} : {ar('اسم المشروع')}", normal_style))
    story.append(Paragraph(f"{ar(extract.contractor_name or '-')} : {ar('اسم المقاول')}", normal_style))
    story.append(Paragraph(f"{ar(extract.unit_number)} : {ar('رقم الوحدة')}", normal_style))
    story.append(Spacer(1, 12))

    # --- Build one continuous table: header once, then each category's items,
    #     with a rotated category label spanning down alongside its own rows ---
    item_col_widths = [2.5 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm, 3.5 * cm]
    label_width = 2 * cm
    col_widths = item_col_widths + [label_width]
    table_width = sum(item_col_widths)

    headers = ["الاجمالي", "نسبة الانجاز", "الفئة", "الكمية", "الوحدة", "بند فرعي"]
    table_data = [[Paragraph(ar(h), header_style) for h in headers] + [Paragraph(ar("بند رئيسي"), header_style)]]

    # Track which row-range in table_data belongs to which category
    category_ranges = []  # list of (start_row, end_row, cat)
    current_row = 1

    for cat in categories:
        items = items_by_cat.get(cat.id, [])
        if not items:
            continue  # nothing to show for this category

        start_row = current_row
        for item in items:
            table_data.append([
                Paragraph(f"{item.total}", cell_style),
                Paragraph(f"{int(item.completion_perc * 100)}%", cell_style),
                Paragraph(ar(int(item.currency)), cell_style),
                Paragraph(f"{int(item.amount)}", cell_style),
                Paragraph(ar(item.unit_type), cell_style),
                Paragraph(ar(item.title), cell_style),
                "",  # placeholder — filled in with the rotated label after measuring row heights
            ])
            current_row += 1
        end_row = current_row - 1
        category_ranges.append((start_row, end_row, cat))

    base_style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        # Striping only applies to the item columns, not the category label column
        ("ROWBACKGROUNDS", (0, 1), (-2, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    # --- Pass 1: measure actual row heights with the placeholder table ---
    measuring_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
    measuring_table.setStyle(TableStyle(base_style_commands))
    measuring_table.wrap(table_width + label_width, 10000 * cm)
    row_heights = measuring_table._rowHeights

    # --- Pass 2: insert the rotated label (sized to its spanned rows) + SPAN commands ---
    span_commands = []
    for start_row, end_row, cat in category_ranges:
        spanned_height = sum(row_heights[start_row:end_row + 1])
        label = VerticalText(
            ar(cat.title),
            font_name="Arabic-Bold",
            font_size=9,
            width=label_width,
            height=spanned_height,
        )
        table_data[start_row][6] = label
        if end_row > start_row:
            span_commands.append(("SPAN", (6, start_row), (6, end_row)))

    final_table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
    final_table.setStyle(TableStyle(base_style_commands + span_commands))

    story.append(final_table)
    story.append(Spacer(1, 16))

    totals_rows = [
        ("اجمالي المستخلص", extract.sub_total),
        ("اجمالي الضرائب", extract.total_taxes),
        ("اجمالي الخصومات", extract.total_deductions),
        ("اجمالي ما سبق صرفه", extract.total_payments),
        ("صافي المستخلص", extract.total),
    ]
    totals_data = [
        [Paragraph(f"{value}", totals_value_style), Paragraph(ar(label), totals_label_style)]
        for label, value in totals_rows
    ]
    totals_table = Table(totals_data, colWidths=[6 * cm, 4 * cm], hAlign="LEFT")
    totals_table.setStyle(TableStyle([
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)
    story.append(Paragraph(f"{ar('مدير المشروع')}", normal_style))

    doc.build(story)
    buffer.seek(0)
    return buffer