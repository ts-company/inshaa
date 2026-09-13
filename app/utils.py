from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
import cloudinary
import cloudinary.uploader
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO



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

    story.append(Paragraph(f"Extract number {extract.id}", styles["Title"]))
    story.append(Paragraph(f"Project: {extract.project_name}", styles["Normal"]))
    story.append(Paragraph(f"Contractor: {extract.contractor_name  or '-'}", styles["Normal"]))
    story.append(Paragraph(f"Unit: {extract.unit_number}", styles["Normal"]))
    story.append(Spacer(1, 12))

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "cell",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        wordWrap="CJK",
    )
    header_style = ParagraphStyle(
        "cell_header",
        parent=cell_style,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    for cat in categories:
        story.append(Paragraph(cat.title, styles["Heading2"]))

        table_data = [[Paragraph(h, header_style) for h in ["Item", "Unit Type", "Amount", "Currency", "Completion %", "Total"]]]
        for item in items_by_cat.get(cat.id, []):
            table_data.append([
                Paragraph(item.title, cell_style),
                Paragraph(item.unit_type, cell_style),
                Paragraph(f"{item.amount}", cell_style),
                Paragraph(f"{item.currency}", cell_style),
                Paragraph(f"{item.completion_perc}%", cell_style),
                Paragraph(f"{item.total}", cell_style),
            ])

        table = Table(table_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm], repeatRows=1, hAlign="CENTER")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(table)
        story.append(Spacer(1, 16))

    totals_data = [
        ["Subtotal", f"{extract.sub_total}"],
        ["Taxes", f"{extract.total_taxes}"],
        ["Deductions", f"{extract.total_deductions}"],
        ["Payments", f"{extract.total_payments}"],
        ["Total", f"{extract.total}"],
    ]
    totals_table = Table(totals_data, colWidths=[4 * cm, 4 * cm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    story.append(totals_table)

    doc.build(story)
    buffer.seek(0)
    return buffer