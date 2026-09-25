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
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO
from app.config import BASE_DIR
from zoneinfo import ZoneInfo

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

def format_rate(rate):
    return f"{round(float(rate) * 100, 2):g}"

def ar(text) -> str:
    if text is None:
        return ""
    text = str(text)
    if not text:
        return text
    return get_display(arabic_reshaper.reshape(text))


def ar_wrap(text, font_name="Arabic", font_size=9, max_width=100) -> str:
    text = "" if text is None else str(text)
    if not text:
        return ""

    words = text.split(" ")
    lines, current = [], []

    def width_of(words_list):
        return stringWidth(ar(" ".join(words_list)), font_name, font_size)

    for word in words:
        candidate = current + [word]
        if current and width_of(candidate) > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current = candidate
    if current:
        lines.append(" ".join(current))

    return "<br/>".join(ar(line) for line in lines)


def generate_extract_pdf(extract, type, categories, items_by_cat, taxes, dedutions, payments) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5 * cm,
        bottomMargin=0.5 * cm,
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
        "cell_header_ar", parent=cell_style, fontName="Arabic-Bold", textColor=colors.white, fontSize=7
    )
    totals_label_style = ParagraphStyle(
        "totals_label_ar", parent=cell_style, fontName="Arabic-Bold"
    )
    totals_value_style = ParagraphStyle(
        "totals_value_ar", parent=cell_style, fontName="Helvetica-Bold", alignment=TA_LEFT
    )
    cat_totals_value_style = ParagraphStyle(
        "cat_totals_value_ar", parent=cell_style, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    net_total_style = ParagraphStyle(
        "net_total_ar", parent=cell_style, fontName="Arabic-Bold", fontSize=13, alignment=TA_LEFT
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


    proj_col_width = 9 * cm
    proj_details_table = Table(
        [
            [Paragraph(f"{ar(extract.contractor_name or '-')} : {ar('اسم المقاول')}", normal_style), Paragraph(f"{ar(extract.project_name)} : {ar('اسم المشروع')}", normal_style)],
            [Paragraph(f"{ar(extract.customer_name or '-')} : {ar('اسم العميل')}", normal_style), Paragraph(f"{ar(extract.contract or '-')} : {ar('العقد')}", normal_style)],
            [Paragraph(f"{ar(extract.job_title)} : {ar('نوع العمل')}", normal_style), Paragraph(f"{ar(extract.unit_number)} : {ar('رقم الوحدة')}", normal_style)],
            [Paragraph(f"{ar(extract.approval_date.astimezone(ZoneInfo('Africa/Cairo')).strftime('%Y/%m/%d'))} {ar('تمت الموافقة في')}", normal_style)],
        ],
        colWidths=[proj_col_width, proj_col_width],
        hAlign="CENTER",
    )
    proj_details_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(KeepTogether([
        proj_details_table,
        Spacer(1, 12),
    ]))

    col_widths = [3 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 8 * cm, 1 * cm]
    title_col_width = col_widths[-2]
    unit_col_width = col_widths[-3]

    item_counter = 1
    for cat in categories:
        items = items_by_cat.get(cat.id, [])
        if not items:
            continue

        heading = Paragraph(ar_wrap(cat.title, "Arabic-Bold", 12, max_width=16 * cm), heading_style)

        headers = ["الاجمالي", "نسبة الانجاز", "الفئة", "الكمية", "الوحدة", "بند فرعي", "رقم البند"]
        table_data = [[Paragraph(ar(h), header_style) for h in headers]]

        cat_total = 0
        for item in items:
            table_data.append([
                Paragraph(f"{item.total}", cell_style),
                Paragraph(f"{format_rate(item.completion_perc)}%", cell_style),
                Paragraph(ar(int(item.currency)), cell_style),
                Paragraph(f"{int(item.amount)}", cell_style),
                Paragraph(
                    ar_wrap(item.unit_type, "Arabic", 9, max_width=unit_col_width - 12),
                    cell_style,
                ),
                Paragraph(
                    ar_wrap(item.title, "Arabic", 9, max_width=title_col_width - 12),
                    cell_style,
                ),
                Paragraph(f"{item_counter}", cell_style),
            ])
            cat_total += item.total
            item_counter += 1

        cat_total_row = len(table_data)
        table_data.append([
            Paragraph(f"{cat_total}", cat_totals_value_style),
            Paragraph(ar("اجمالي البند"), totals_label_style),
            "", "", "", "",
        ])

        table = Table(
            table_data,
            colWidths=col_widths,
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

    # ============================================================
    # Taxes / deductions / payments — 3-column detail table
    # (amount, rate, title) — plain, no header row, no coloring
    # ============================================================

    detail_col_widths = [3 * cm, 1.5 * cm, 4 * cm]  # amount, rate, title
    detail_title_width = detail_col_widths[-1]

    detail_data = []

    detail_data.append([
        Paragraph(f"{extract.sub_total}", totals_value_style),
        Paragraph("", totals_value_style),
        Paragraph(ar_wrap("اجمالي المستخلص", "Arabic-Bold", 9, max_width=detail_title_width - 12), totals_label_style),
    ])

    for t in taxes:
        detail_data.append([
            Paragraph(f"{round(t.rate * extract.sub_total, 2)}", totals_value_style),
            Paragraph(f"{format_rate(t.rate)}%", totals_value_style),
            Paragraph(ar_wrap(t.title, "Arabic-Bold", 9, max_width=detail_title_width - 12), totals_label_style),
        ])

    for d in dedutions:
        detail_data.append([
            Paragraph(f"{d.amount if d.amount is not None else round(d.rate*extract.sub_total, 2)}" , totals_value_style),
            Paragraph(f"{format_rate(d.rate)}%" if d.rate is not None else "" , totals_value_style),
            Paragraph(ar_wrap(d.title, "Arabic-Bold", 9, max_width=detail_title_width - 12), totals_label_style),
        ])

    for p in payments:
        detail_data.append([
            Paragraph(f"{p.amount}", totals_value_style),
            Paragraph("", totals_value_style),
            Paragraph(ar_wrap(p.details, "Arabic-Bold", 9, max_width=detail_title_width - 12), totals_label_style),
        ])

    detail_data.append([
        Paragraph(f"{extract.total_payments + extract.total_deductions + extract.total_taxes}", totals_value_style),
        Paragraph("", totals_value_style),
        Paragraph(ar_wrap("اجمالي الاستقطاعات", "Arabic-Bold", 9, max_width=detail_title_width - 12), totals_label_style),
    ])

    detail_data.append([
        Paragraph(f"{extract.total}", totals_value_style),
        Paragraph("", totals_value_style),
        Paragraph(ar_wrap("صافي المستخلص", "Arabic-Bold", 9, max_width=detail_title_width - 12), totals_label_style),
    ])

    detail_table = Table(detail_data, colWidths=detail_col_widths, hAlign="LEFT")
    detail_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    sign_style = ParagraphStyle(
        "sign_ar", parent=normal_style, alignment=TA_CENTER
    )
    signature_col_width = 6.5 * cm
    signature_table = Table(
        [[
            Paragraph(ar("مدير حسابات"), sign_style),  # leftmost
            Paragraph(ar("مهندس موقع"), sign_style),  # middle
            Paragraph(ar("مدير المشروع"), sign_style),  # rightmost
        ]],
        colWidths=[signature_col_width, signature_col_width, signature_col_width],
        hAlign="CENTER",
    )
    signature_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(KeepTogether([
        detail_table,
        Spacer(1, 12),
        signature_table,
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
            Paragraph(ar(extract.job_title), cell_style),
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