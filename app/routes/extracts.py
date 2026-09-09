from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.permissions_model import Permission
from app.models.extracts.extracts import Extract
from app.models.extracts.exctracts_category import ExtractCategory
from app.models.extracts.extract_category_item import ExtractCategoryItem
from app.models.extracts.extract_previously_paid import ExtractPreviouslyPaid
from app.models.extracts.extracts_taxes import ExtractTaxes
from app.models.extracts.extracts_deductions import ExtractDeduction
from app.schemas.exctract import AddExtract, AddExtractCategory, AddExtractCategoryItem, AddExtractTax, AddExtractDeduction, PreviouslyPaid
from app.core.auth import validate_user
from app.database import get_db
from app.config import BASE_DIR
from decimal import Decimal
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/system/extracts")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def get_extracts(request: Request, id: int = None, name: str = None, contractor: str = None, unit: int = None, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    query = db.query(Extract)

    if id is not None:
        query = query.filter(Extract.id == id)

    if name:
        query = query.filter(Extract.project_name.ilike(f"%{name}%"))

    if contractor:
        query = query.filter(Extract.contractor_name.ilike(f"%{contractor}%"))

    if unit:
        query = query.filter(Extract.unit_number.ilike(f"%{unit}%"))

    extracts = [
        {
            "id": e.id,
            "project_name": e.project_name,
            "unit_number": e.unit_number,
            "contractor_name": e.contractor_name,
            "sub_total": e.sub_total,
            "total_taxes": e.total_taxes,
            "total_deductions": e.total_deductions,
            "total": e.total
        }
        for e in query.order_by(Extract.id.desc()).all()
    ]
    return templates.TemplateResponse("extracts.html", {"request": request, "extracts": extracts})


@router.get("/details/{ext_id}")
def get_extracts(request: Request, ext_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    categories = db.query(ExtractCategory).filter(ExtractCategory.extract_id == extract.id).all()
    categories_ids = [row.id for row in categories]

    all_items = db.query(ExtractCategoryItem).filter(ExtractCategoryItem.category_id.in_(categories_ids)).all()
    items_by_category = {}
    for item in all_items:
        items_by_category.setdefault(item.category_id, []).append({
            "id": item.id,
            "title": item.title,
            "unit_type": item.unit_type,
            "amount": item.amount,
            "currency": item.currency,
            "completion_perc": item.completion_perc,
            "total": item.total
        })

    category_dicts = [
        {
            "id": cat.id,
            "title": cat.title,
            "items": items_by_category.get(cat.id, [])
        }
        for cat in categories
    ]

    previously_paid = [
        {
            "id": pp.id,
            "date": pp.date.astimezone(ZoneInfo("Africa/Cairo")).strftime("%B %d, %Y"),
            "amount": pp.amount
        }
        for pp in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()
    ]

    taxes = [
        {
            "id": t.id,
            "title": t.title,
            "rate": t.rate,
        }
        for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()
    ]

    deductions = [
        {
            "id": d.id,
            "title": d.title,
            "amount": d.amount
        }
        for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()
    ]


    extract = {
            "id": extract.id,
            "project_name": extract.project_name,
            "unit_number": extract.unit_number,
            "contractor_name": extract.contractor_name,
            "sub_total": extract.sub_total,
            "total_taxes": extract.total_taxes,
            "total_deductions": extract.total_deductions,
            "total": extract.total,
            "categories": category_dicts,
            "previously_paid": previously_paid,
            "taxes": taxes,
            "deductions": deductions
        }

    return templates.TemplateResponse("extract_details.html", {"request": request, "extract": extract})

@router.post("/add_extract")
def add_extracts(request: Request, payload: AddExtract, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        new_extract = Extract(
            project_name=payload.project_name,
            unit_number=payload.unit_number,
            contractor_name=payload.contractor_name,
            sub_total=0,
            total_taxes=0,
            total_deductions=0,
            total=0
        )

        db.add(new_extract)
        db.flush()
        for tax in payload.taxes:
            db.add(ExtractTaxes(extract_id=new_extract.id, title=tax.title, rate=tax.rate))

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == new_extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == new_extract.id).all()),
            Decimal("0"),
        )
        new_extract.total_deductions = total_deductions + total_payments
        new_extract.total = new_extract.sub_total - (total_deductions + total_payments)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/add_category/{ext_id}")
def add_cat(request: Request, ext_id: int, payload: AddExtractCategory, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).with_for_update().first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        new_category = ExtractCategory(
            extract_id=extract.id,
            title=payload.title
        )
        db.add(new_category)
        db.flush()
        items_total = 0
        for item in payload.items:
            item_total = round(item.amount * item.currency * item.completion_perc, 2)
            db.add(ExtractCategoryItem(
                    category_id=new_category.id,
                    title=item.title,
                    unit_type=item.unit_type,
                    amount=item.amount,
                    currency=item.currency,
                    completion_perc=item.completion_perc,
                    total=item_total
                ))
            items_total += item_total
        extract.sub_total += items_total

        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        )
        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_deductions + total_taxes + total_payments)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/add_item/{cat_id}")
def add_item(request: Request, cat_id: int, payload: AddExtractCategoryItem, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = db.query(ExtractCategory, Extract).join(Extract, Extract.id == ExtractCategory.extract_id).filter(ExtractCategory.id == cat_id).with_for_update().first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    cat, extract = result

    item_total = round(payload.amount * payload.currency * payload.completion_perc, 2)
    try:
        new_item = ExtractCategoryItem(category_id=cat.id, title=payload.title, unit_type=payload.unit_type,
                                       amount=payload.amount, currency=payload.currency, completion_perc=payload.completion_perc,
                                       total=item_total)
        db.add(new_item)
        extract.sub_total += item_total

        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_deductions + total_taxes + total_payments)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_category/{cat_id}")
def del_cat(request: Request, cat_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = db.query(ExtractCategory, Extract).join(Extract, Extract.id == ExtractCategory.extract_id).filter(ExtractCategory.id == cat_id).with_for_update().first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    cat, extract = result

    try:
        items_total = sum((item.total for item in db.query(ExtractCategoryItem).filter(ExtractCategoryItem.category_id == cat_id).all()), Decimal('0'))
        extract.sub_total -= items_total

        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_taxes + total_deductions + total_payments)
        db.delete(cat)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_item/{item_id}")
def del_item(request: Request, item_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = (db.query(ExtractCategoryItem, Extract)
              .join(ExtractCategory, ExtractCategory.id == ExtractCategoryItem.category_id)
              .join(Extract, Extract.id == ExtractCategory.extract_id)
              .filter(ExtractCategoryItem.id == item_id)
              .with_for_update()
              .first())

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    item, extract = result

    try:
        extract.sub_total -= item.total

        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_taxes + total_deductions + total_payments)
        db.delete(item)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/add_tax/{ext_id}")
def add_tax(request: Request, ext_id: int, payload: AddExtractTax, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).with_for_update().first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        new_tax = ExtractTaxes(extract_id=extract.id, title=payload.title, rate=payload.rate)
        db.add(new_tax)

        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        ) + payload.rate
        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_taxes + total_deductions + total_payments)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_tax/{tax_id}")
def del_tax(request: Request, tax_id: int,  db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = (db.query(ExtractTaxes, Extract)
              .join(Extract, Extract.id == ExtractTaxes.extract_id)
              .filter(ExtractTaxes.id == tax_id)
              .with_for_update()
              .first())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    tax, extract = result

    try:
        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id, ExtractTaxes.id != tax_id).all()),
            Decimal("0"),
        )
        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_taxes + total_deductions + total_payments)
        db.delete(tax)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/add_ded/{ext_id}")
def add_ded(request: Request, ext_id: int, payload: AddExtractDeduction, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).with_for_update().first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        new_ded = ExtractDeduction(extract_id=extract.id, title=payload.title, amount=payload.amount)
        db.add(new_ded)

        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        )
        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        ) + payload.amount

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_taxes + total_deductions + total_payments)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_ded/{ded_id}")
def del_ded(request: Request, ded_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = (db.query(ExtractDeduction, Extract)
              .join(Extract, Extract.id == ExtractDeduction.extract_id)
              .filter(ExtractDeduction.id == ded_id)
              .with_for_update()
              .first())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    ded, extract = result

    try:
        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        )
        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id, ExtractDeduction.id != ded_id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_taxes + total_deductions + total_payments)
        db.delete(ded)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/add_payment/{ext_id}")
def add_payment(request: Request, ext_id: int, payload: PreviouslyPaid, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).with_for_update().first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        new_paid = ExtractPreviouslyPaid(extract_id=extract.id, date=datetime.now(timezone.utc), amount=payload.amount)
        db.add(new_paid)

        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        )
        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()),
            Decimal("0"),
        ) + payload.amount

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_taxes + total_deductions + total_payments)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_payment/{pay_id}")
def del_payment(request: Request, pay_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "manage extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = (db.query(ExtractPreviouslyPaid, Extract)
              .join(Extract, Extract.id == ExtractPreviouslyPaid.extract_id)
              .filter(ExtractPreviouslyPaid.id == pay_id)
              .with_for_update()
              .first())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    paid, extract = result

    try:
        total_rates = sum(
            (t.rate for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()),
            Decimal("0"),
        )
        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = sum(
            (d.amount for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()),
            Decimal("0"),
        )

        total_payments = sum(
            (p.amount for p in
             db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id, ExtractPreviouslyPaid.id != pay_id).all()),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions + total_payments
        extract.total = extract.sub_total - (total_taxes + total_deductions + total_payments)
        db.delete(paid)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}