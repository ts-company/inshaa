from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
import cloudinary
import cloudinary.uploader
import os
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Image as RLImage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import KeepTogether
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


ALLOWED_PFP_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
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
        if image.format not in {"JPEG", "PNG", "WEBP", "JPG"}:
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


def generate_extract_pdf(extract, type, categories, items_by_cat, taxes, dedutions, payments) -> BytesIO:
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
    heading_style = ParagraphStyle(
        "heading_ar", parent=styles["Heading2"], fontName="Arabic-Bold", alignment=TA_RIGHT
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
    cat_totals_value_style = ParagraphStyle(
        "totals_value_ar", parent=cell_style, fontName="Helvetica-Bold", alignment=TA_CENTER
    )

    logo_path = os.path.join(BASE_DIR, "static", "pdf_logo.png")
    logo = RLImage(logo_path, width=7 * cm, height=2 * cm)

    if type == "active":
        header_text = Paragraph(f"{extract.id} {ar('مستخلص')}", title_style)
    elif type == "history":
        header_text = Paragraph(f"{extract.id} {ar('نسخة تم تعديلها')}", title_style)
    else:
        header_text = Paragraph(f"{extract.id} {ar('نسخة قديمة')}", title_style)

    header_table = Table(
        [[logo, header_text]],
        colWidths=[4 * cm, 12 * cm]
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"{ar(extract.project_name)} : {ar('اسم المشروع')}", normal_style))
    story.append(Paragraph(f"{ar(extract.contract)} : {ar('العقد')}", normal_style))
    story.append(Paragraph(f"{ar(extract.contractor_name or '-')} : {ar('اسم المقاول')}", normal_style))
    story.append(Paragraph(f"{ar(extract.customer_name or '-')} : {ar('اسم العميل')}", normal_style))
    story.append(Paragraph(f"{ar(extract.unit_number)} : {ar('رقم الوحدة')}", normal_style))
    story.append(Spacer(1, 12))

    for cat in categories:
        items = items_by_cat.get(cat.id, [])
        if not items:
            continue

        heading = Paragraph(ar(cat.title), heading_style)

        headers = ["الاجمالي", "نسبة الانجاز", "الفئة", "الكمية", "الوحدة", "بند فرعي"]
        table_data = [[Paragraph(ar(h), header_style) for h in headers]]

        cat_total = 0
        for item in items:
            table_data.append([
                Paragraph(f"{item.total}", cell_style),
                Paragraph(f"{int(item.completion_perc * 100)}%", cell_style),
                Paragraph(ar(int(item.currency)), cell_style),
                Paragraph(f"{int(item.amount)}", cell_style),
                Paragraph(ar(item.unit_type), cell_style),
                Paragraph(ar(item.title), cell_style),
            ])
            cat_total += item.total

        cat_total_row = len(table_data)
        table_data.append([
            Paragraph(f"{cat_total}", cat_totals_value_style),
            Paragraph(ar("اجمالي البند"), totals_label_style),
            "", "", "", "",
        ])

        table = Table(
            table_data,
            colWidths=[3 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 4 * cm],
            repeatRows=1,
            hAlign="CENTER"
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            # zebra striping only over the item rows, not the total row
            ("ROWBACKGROUNDS", (0, 1), (-1, cat_total_row - 1), [colors.white, colors.HexColor("#f2f2f2")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            # category total row: merge the label across the 5 non-total columns
            ("SPAN", (1, cat_total_row), (-1, cat_total_row)),
            ("BACKGROUND", (0, cat_total_row), (-1, cat_total_row), colors.HexColor("#dfe6ea")),
            ("LINEABOVE", (0, cat_total_row), (-1, cat_total_row), 1, colors.black),
        ]))

        story.append(KeepTogether([heading, table]))
        story.append(Spacer(1, 16))

    totals_rows = [("اجمالي المستخلص", extract.sub_total)] + [(f"{t.title}", f"{int(t.rate * 100)}%") for t in taxes] +\
        [("اجمالي الضرائب", extract.total_taxes)] + [(f"{d.title}", f"{int(d.rate * 100)}%" if d.rate is not None else d.amount) for d in dedutions] +\
        [("اجمالي الخصومات", extract.total_deductions)] +\
        [(f"{p.details}", p.amount) for p in payments] +\
        [("اجمالي ما سبق صرفه", extract.total_payments)] + \
        [("اجمالي الخصومات و ما سبق صرفه", extract.total_payments + extract.total_deductions)] + \
        [("صافي المستخلص", extract.total)]

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

    story.append(KeepTogether([
        totals_table,
        Paragraph(f"{ar('مدير المشروع')}", normal_style),
    ]))

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_summary_pdf(extracts) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "title_ar", parent=styles["Title"], fontName="Arabic-Bold", alignment=TA_RIGHT
    )
    cell_style = ParagraphStyle(
        "cell_ar", parent=styles["Normal"], fontName="Arabic", fontSize=9,
        leading=13, alignment=TA_RIGHT, wordWrap="RTL"
    )
    header_style = ParagraphStyle(
        "cell_header_ar", parent=cell_style, fontName="Arabic-Bold", textColor=colors.white
    )

    logo_path = os.path.join(BASE_DIR, "static", "pdf_logo.png")
    logo = RLImage(logo_path, width=7 * cm, height=2 * cm)
    header_text = Paragraph(ar("ملخص"), title_style)

    header_table = Table([[logo, header_text]], colWidths=[4 * cm, 12 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))

    headers = ["الصافي", "الاجمالي", "رقم الوحدة", "نوع العمل", "اسم المقاول", "اسم المشروع", "ID"]
    table_data = [[Paragraph(ar(h), header_style) for h in headers]]

    for extract in extracts:
        table_data.append([
            Paragraph(f"{extract.total}", cell_style),
            Paragraph(f"{extract.sub_total}", cell_style),
            Paragraph(f"{extract.unit_number}", cell_style),
            Paragraph(f"{extract.job_title}", cell_style),
            Paragraph(ar(extract.contractor_name or "-"), cell_style),
            Paragraph(ar(extract.project_name), cell_style),
            Paragraph(f"{extract.id}", cell_style),
        ])

    table = Table(
        table_data,
        colWidths=[2.5 * cm, 2.5 * cm, 2 * cm, 3 * cm, 3 * cm, 3 * cm, 1.5 * cm],
        repeatRows=1,
        hAlign="CENTER"
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer