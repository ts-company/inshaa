from fastapi import APIRouter, Depends, status, HTTPException, Request, Body
from fastapi.responses import StreamingResponse
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
from app.models.extracts.extract_history import ExtractHistory
from app.models.extracts.history_category import ExtractCategoryHistory
from app.models.extracts.history_category_item import ExtractCategoryItemHistory
from app.models.extracts.taxes_history import ExtractTaxesHistory
from app.models.extracts.deductions_history import ExtractDeductionHistory
from app.models.extracts.payments_history import ExtractPreviouslyPaidHistory
from app.schemas.exctract import AddExtract, AddExtractCategories, UpdateAccounting
from app.core.auth import validate_user
from app.utils import generate_extract_pdf, generate_summary_pdf
from app.database import get_db
from app.config import BASE_DIR
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import List

router = APIRouter(prefix="/system/extracts")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def get_extracts(request: Request, id: int = None, name: str = None, contractor: str = None, customer: str = None, unit: int = None, job_title: str = None, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    permission_types = [p.type for p in db.query(Permission).filter(Permission.user_id == user_id).all()]
    if user.role != "super_admin":
        if "generate pdf" not in permission_types and\
                "edit extracts" not in permission_types and\
                "approve extracts" not in permission_types and\
                "accounting" not in permission_types and\
                "add extracts" not in permission_types and\
                "delete extracts" not in permission_types and\
                "extracts history" not in permission_types:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if user_role == "super_admin":
        query = db.query(Extract)
    else:
        query = db.query(Extract).filter(Extract.created_by == user_id)

    if id is not None:
        query = query.filter(Extract.id == id)

    if name:
        query = query.filter(Extract.project_name.ilike(f"%{name}%"))

    if contractor:
        query = query.filter(Extract.contractor_name.ilike(f"%{contractor}%"))

    if customer:
        query = query.filter(Extract.contractor_name.ilike(f"%{customer}%"))

    if unit:
        query = query.filter(Extract.unit_number == unit)

    if job_title:
        query = query.filter(Extract.job_title.ilike(f"%{job_title}%"))

    extracts = [
        {
            "id": e.id,
            "project_name": e.project_name,
            "unit_number": e.unit_number,
            "contractor_name": e.contractor_name,
            "job_title": e.job_title,
            "sub_total": e.sub_total,
            "total_taxes": e.total_taxes,
            "total_deductions": e.total_deductions,
            "total_payments": e.total_payments,
            "total": e.total
        }
        for e in query.order_by(Extract.id.desc()).all()
    ]
    return templates.TemplateResponse("extracts.html", {"request": request, "extracts": extracts})

@router.post("/get_summary")
def get_extracts(request: Request, ext_ids: List[int] = Body(...), db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    permission_types = [p.type for p in db.query(Permission).filter(Permission.user_id == user_id).all()]
    if user.role != "super_admin":
        if "generate pdf" not in permission_types:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extracts = db.query(Extract).filter(Extract.id.in_(ext_ids)).order_by(Extract.id).all()
    try:
        pdf_buffer = generate_summary_pdf(extracts)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=extracts_summary.pdf"}
    )

@router.post("/weekly_summary")
def get_extracts(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    permission_types = [p.type for p in db.query(Permission).filter(Permission.user_id == user_id).all()]
    if user.role != "super_admin":
        if "generate pdf" not in permission_types:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    now = datetime.now(timezone.utc)
    days_since_sunday = now.isoweekday() % 7
    start_of_week = (now - timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)

    extracts = db.query(Extract).filter(Extract.created_at >= start_of_week).all()

    try:
        pdf_buffer = generate_summary_pdf(extracts, now.astimezone(ZoneInfo("Africa/Cairo")).strftime("%B %d, %Y"),)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=extracts_summary.pdf"}
    )


@router.get("/details/{ext_id}")
def get_extracts(request: Request, ext_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    permission_types = [p.type for p in db.query(Permission).filter(Permission.user_id == user_id).all()]
    if user.role != "super_admin":
        if "edit extracts" not in permission_types and\
                "generate pdf" not in permission_types and\
                "approve extracts" not in permission_types and\
                "accounting" not in permission_types and\
                "add extracts" not in permission_types and\
                "delete extracts" not in permission_types and\
                "extracts history" not in permission_types:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    categories = db.query(ExtractCategory).filter(ExtractCategory.extract_id == extract.id).order_by(ExtractCategory.id).all()
    categories_ids = [row.id for row in categories]

    all_items = db.query(ExtractCategoryItem).filter(ExtractCategoryItem.category_id.in_(categories_ids)).order_by(ExtractCategoryItem.id).all()
    items_by_category = {}
    for item in all_items:
        items_by_category.setdefault(item.category_id, []).append({
            "id": item.id,
            "title": item.title,
            "unit_type": item.unit_type,
            "amount": item.amount,
            "currency": item.currency,
            "completion_perc": int(item.completion_perc * 100),
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
            "details": pp.details,
            "amount": pp.amount
        }
        for pp in db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()
    ]

    taxes = [
        {
            "id": t.id,
            "title": t.title,
            "rate": int(t.rate*100),
            "amount": t.rate * extract.sub_total
        }
        for t in db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()
    ]

    deductions = [
        {
            "id": d.id,
            "title": d.title,
            "amount": d.amount,
            "rate": d.rate
        }
        for d in db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()
    ]


    extract = {
            "id": extract.id,
            "project_name": extract.project_name,
            "unit_number": extract.unit_number,
            "contractor_name": extract.contractor_name,
            "customer_name": extract.customer_name,
            "job_title": extract.job_title,
            "sub_total": extract.sub_total,
            "total_taxes": extract.total_taxes,
            "total_deductions": extract.total_deductions,
            "total_payments": extract.total_payments,
            "total": extract.total,
            "categories": category_dicts,
            "previously_paid": previously_paid,
            "taxes": taxes,
            "deductions": deductions,
            "approved": extract.approved
        }

    return templates.TemplateResponse("extract_details.html", {"request": request, "extract": extract, "history": False, "permissions": permission_types})


@router.get("/details_hist/{history_id}")
def get_extracts(request: Request, history_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "extracts history").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission_types = [p.type for p in db.query(Permission).filter(Permission.user_id == user_id).all()]

    result = (db.query(ExtractHistory, User)
               .outerjoin(User, User.id == ExtractHistory.updated_by)
               .filter(ExtractHistory.id == history_id)
               .first())

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    extract, updated_by = result
    updated_by_name = f"{updated_by.first_name} {updated_by.last_name}" if updated_by is not None else "غير معروف"

    categories = db.query(ExtractCategoryHistory).filter(ExtractCategoryHistory.extract_history_id == extract.id).all()
    categories_ids = [row.id for row in categories]

    all_items = db.query(ExtractCategoryItemHistory).filter(ExtractCategoryItemHistory.extract_category_history_id.in_(categories_ids)).all()
    items_by_category = {}
    for item in all_items:
        items_by_category.setdefault(item.extract_category_history_id, []).append({
            "id": item.id,
            "title": item.title,
            "unit_type": item.unit_type,
            "amount": item.amount,
            "currency": item.currency,
            "completion_perc": int(item.completion_perc * 100),
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
            "details": pp.details,
            "amount": pp.amount
        }
        for pp in db.query(ExtractPreviouslyPaidHistory).filter(ExtractPreviouslyPaidHistory.extract_history_id == extract.id).all()
    ]

    taxes = [
        {
            "id": t.id,
            "title": t.title,
            "rate": int(t.rate*100),
            "amount": t.rate * extract.sub_total
        }
        for t in db.query(ExtractTaxesHistory).filter(ExtractTaxesHistory.extract_history_id == extract.id).all()
    ]

    deductions = [
        {
            "id": d.id,
            "title": d.title,
            "amount": d.amount,
            "rate": d.rate
        }
        for d in db.query(ExtractDeductionHistory).filter(ExtractDeductionHistory.extract_history_id == extract.id).all()
    ]


    extract = {
            "id": extract.id,
            "project_name": extract.project_name,
            "unit_number": extract.unit_number,
            "contractor_name": extract.contractor_name,
            "customer_name": extract.customer_name,
            "updated_by": updated_by_name,
            "updated_at": extract.updated_at.astimezone(ZoneInfo("Africa/Cairo")).strftime("%B %d, %Y"),
            "job_title": extract.job_title,
            "sub_total": extract.sub_total,
            "total_taxes": extract.total_taxes,
            "total_deductions": extract.total_deductions,
            "total_payments": extract.total_payments,
            "total": extract.total,
            "categories": category_dicts,
            "previously_paid": previously_paid,
            "taxes": taxes,
            "deductions": deductions
        }

    return templates.TemplateResponse("extract_details.html", {"request": request, "extract": extract, "history": True, "permissions": permission_types})


@router.get("/histories/{ext_id}")
def get_histories(request: Request, ext_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "extracts history").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    results = (db.query(ExtractHistory, User)
               .outerjoin(User, User.id == ExtractHistory.updated_by)
               .filter(ExtractHistory.extract_id == extract.id)
               .order_by(ExtractHistory.id.desc())
               .all())

    return [
        {
            "id": h.id,
            "updated_by": f"{u.first_name} {u.last_name}" if u is not None else None,
            "updated_at": h.updated_at.astimezone(ZoneInfo("Africa/Cairo")).strftime("%B %d, %Y"),
            "sub_total": h.sub_total
        }
        for h, u in results
    ]

@router.post("/add_extract")
def add_extracts(request: Request, payload: AddExtract, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "add extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        new_extract = Extract(
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            project_name=payload.project_name,
            unit_number=payload.unit_number,
            contractor_name=payload.contractor_name,
            customer_name=payload.customer_name,
            job_title=payload.job_title,
            sub_total=0,
            total_taxes=0,
            total_deductions=0,
            total_payments=0,
            total=0,
            approved=True
        )

        db.add(new_extract)
        db.flush()

        items_total = Decimal("0")
        for cat in payload.categories:
            new_cat = ExtractCategory(extract_id=new_extract.id, title=cat.title)
            db.add(new_cat)
            db.flush()
            for item in cat.items:
                if (item.prev_amount + item.current_amount) > item.total_amount:
                    raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE)
                item_total = round(item.total_amount * item.currency * item.completion_perc, 2)
                db.add(ExtractCategoryItem(
                    category_id=new_cat.id,
                    title=item.title,
                    unit_type=item.unit_type,
                    prev_amount=item.prev_amount,
                    current_amount=item.current_amount,
                    total_amount=item.total_amount,
                    currency=item.currency,
                    completion_perc=item.completion_perc,
                    total=item_total
                ))
                items_total += item_total

        new_extract.sub_total += items_total

        total_rates = Decimal("0")
        for tax in payload.taxes:
            db.add(ExtractTaxes(extract_id=new_extract.id, title=tax.title, rate=tax.rate))
            total_rates += tax.rate
        total_taxes = round(total_rates*new_extract.sub_total, 2)

        total_deductions = Decimal("0")
        total_ded_rates = Decimal("0")
        for ded in payload.deductions:
            if ded.rate is not None and ded.amount is not None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
            if ded.rate is None and ded.amount is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if ded.rate is not None:
                db.add(ExtractDeduction(extract_id=new_extract.id, title=ded.title, rate=ded.rate))
                total_ded_rates += ded.rate
            else:
                db.add(ExtractDeduction(extract_id=new_extract.id, title=ded.title, amount=ded.amount))
                total_deductions += ded.amount

        total_deductions += round(total_ded_rates * new_extract.sub_total, 2)

        total_payments = Decimal("0")
        for pp in payload.payments:
            db.add(ExtractPreviouslyPaid(extract_id=new_extract.id, details=pp.details, amount=pp.amount))
            total_payments += pp.amount

        new_extract.total_taxes = total_taxes
        new_extract.total_deductions = total_deductions
        new_extract.total_payments = total_payments
        new_extract.total = (new_extract.sub_total + total_taxes) - (total_deductions + total_payments)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/edit_extract/{ext_id}")
def add_cat(request: Request, ext_id: int, payload:AddExtractCategories, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "edit extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).with_for_update().first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    old_cats = db.query(ExtractCategory).filter(ExtractCategory.extract_id == extract.id).all()
    old_cats_ids = [cat.id for cat in old_cats]
    old_items = db.query(ExtractCategoryItem).filter(ExtractCategoryItem.category_id.in_(old_cats_ids)).all()

    old_items_by_cat = {}
    for old_item in old_items:
        old_items_by_cat.setdefault(old_item.category_id, []).append(old_item)

    old_taxes = db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()
    old_deductions = db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()
    old_payments = db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()

    try:
        history = ExtractHistory(
            extract_id=extract.id,
            updated_at=datetime.now(timezone.utc),
            updated_by=user_id,
            project_name=extract.project_name,
            unit_number=extract.unit_number,
            contractor_name=extract.contractor_name,
            customer_name=extract.customer_name,
            job_title=extract.job_title,
            sub_total=extract.sub_total,
            total_taxes=extract.total_taxes,
            total_deductions=extract.total_deductions,
            total_payments=extract.total_payments,
            total=extract.total
        )
        db.add(history)
        db.flush()
        for old_cat in old_cats:
            history_cat = ExtractCategoryHistory(
                extract_history_id=history.id,
                title=old_cat.title
            )
            db.add(history_cat)
            db.flush()
            db.delete(old_cat)
            for old_item in old_items_by_cat.get(old_cat.id, []):
                db.add(ExtractCategoryItemHistory(
                    extract_category_history_id=history_cat.id,
                    title=old_item.title,
                    unit_type=old_item.unit_type,
                    prev_amount=old_item.prev_amount,
                    current_amount=old_item.current_amount,
                    total_amount=old_item.total_amount,
                    currency=old_item.currency,
                    completion_perc=old_item.completion_perc,
                    total=old_item.total
                ))

        for t in old_taxes:
            db.add(ExtractTaxesHistory(extract_history_id=history.id, title=t.title, rate=t.rate))
        for d in old_deductions:
            if d.rate is not None:
                db.add(ExtractDeductionHistory(extract_history_id=history.id, title=d.title, rate=d.rate))
            else:
                db.add(ExtractDeductionHistory(extract_history_id=history.id, title=d.title, amount=d.amount))
        for p in old_payments:
            db.add(ExtractPreviouslyPaidHistory(extract_history_id=history.id, details=p.details, amount=p.amount))

        items_total = Decimal("0")
        for cat in payload.categories:
            new_cat = ExtractCategory(extract_id=extract.id, title=cat.title)
            db.add(new_cat)
            db.flush()
            for item in cat.items:
                if (item.prev_amount + item.current_amount) > item.total_amount:
                    raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE)
                item_total = round(item.currency * item.total_amount * item.completion_perc, 2)
                db.add(ExtractCategoryItem(
                    category_id=new_cat.id,
                    title=item.title,
                    unit_type=item.unit_type,
                    prev_amount=item.prev_amount,
                    current_amount=item.current_amount,
                    total_amount=item.total_amount,
                    currency=item.currency,
                    completion_perc=item.completion_perc,
                    total=item_total
                ))
                items_total += item_total
        extract.sub_total = items_total

        total_rates = sum(
            (t.rate for t in old_taxes),
            Decimal("0"),
        )
        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = Decimal("0")
        total_ded_rates = Decimal("0")
        for d in old_deductions:
            if d.rate is not None:
                total_ded_rates += d.rate
            else:
                total_deductions += d.amount
        total_deductions += round(total_ded_rates * extract.sub_total, 2)

        total_payments = sum(
            (p.amount for p in old_payments),
            Decimal("0"),
        )

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions
        extract.total_payments = total_payments
        extract.total = (extract.sub_total + total_taxes) - (total_deductions + total_payments)
        extract.approved = False
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_extract/{ext_id}")
def add_cat(request: Request, ext_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "delete extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).with_for_update().first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        db.delete(extract)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/edit_accounting/{ext_id}")
def add_tax(request: Request, ext_id: int, payload: UpdateAccounting, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "accounting").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).with_for_update().first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    old_cats = db.query(ExtractCategory).filter(ExtractCategory.extract_id == extract.id).all()
    old_cats_ids = [cat.id for cat in old_cats]
    old_items = db.query(ExtractCategoryItem).filter(ExtractCategoryItem.category_id.in_(old_cats_ids)).all()

    old_taxes = db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()
    old_deductions = db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()
    old_payments = db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()

    old_items_by_cat = {}
    for old_item in old_items:
        old_items_by_cat.setdefault(old_item.category_id, []).append(old_item)

    history = ExtractHistory(
        extract_id=extract.id,
        updated_at=datetime.now(timezone.utc),
        updated_by=user_id,
        project_name=extract.project_name,
        unit_number=extract.unit_number,
        contractor_name=extract.contractor_name,
        customer_name=extract.customer_name,
        job_title=extract.job_title,
        sub_total=extract.sub_total,
        total_taxes=extract.total_taxes,
        total_deductions=extract.total_deductions,
        total_payments=extract.total_payments,
        total=extract.total
    )
    db.add(history)
    db.flush()
    for old_cat in old_cats:
        history_cat = ExtractCategoryHistory(
            extract_history_id=history.id,
            title=old_cat.title
        )
        db.add(history_cat)
        db.flush()
        for old_item in old_items_by_cat.get(old_cat.id, []):
            db.add(ExtractCategoryItemHistory(
                extract_category_history_id=history_cat.id,
                title=old_item.title,
                unit_type=old_item.unit_type,
                prev_amount=old_item.prev_amount,
                current_amount=old_item.current_amount,
                total_amount=old_item.total_amount,
                currency=old_item.currency,
                completion_perc=old_item.completion_perc,
                total=old_item.total
            ))

    for t in old_taxes:
        db.add(ExtractTaxesHistory(extract_history_id=history.id, title=t.title, rate=t.rate))
        db.delete(t)
    for d in old_deductions:
        if d.rate is not None:
            db.add(ExtractDeductionHistory(extract_history_id=history.id, title=d.title, rate=d.rate))
        else:
            db.add(ExtractDeductionHistory(extract_history_id=history.id, title=d.title, amount=d.amount))
        db.delete(d)
    for p in old_payments:
        db.add(ExtractPreviouslyPaidHistory(extract_history_id=history.id, details=p.details, amount=p.amount))
        db.delete(p)

    try:
        total_rates = Decimal("0")
        for tax in payload.taxes:
            total_rates += tax.rate
            db.add(ExtractTaxes(extract_id=extract.id, title=tax.title, rate=tax.rate))

        total_taxes = round(total_rates * extract.sub_total, 2)

        total_deductions = Decimal("0")
        total_ded_rates = Decimal("0")
        for ded in payload.deductions:

            if ded.rate is not None and ded.amount is not None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
            if ded.rate is None and ded.amount is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if ded.rate is not None:
                total_ded_rates += ded.rate
                db.add(ExtractDeduction(extract_id=extract.id, title=ded.title, rate=ded.rate))
            else:
                total_deductions += ded.amount
                db.add(ExtractDeduction(extract_id=extract.id, title=ded.title, amount=ded.amount))
        total_deductions += round(total_ded_rates * extract.sub_total, 2)

        total_payments = Decimal("0")
        for payment in payload.payments:
            total_payments += payment.amount
            db.add(ExtractPreviouslyPaid(extract_id=extract.id, details=payment.details, amount=payment.amount))

        extract.total_taxes = total_taxes
        extract.total_deductions = total_deductions
        extract.total_payments = total_payments
        extract.total = (extract.sub_total + total_taxes) - (total_deductions + total_payments)
        extract.approved = False
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/approve/{ext_id}")
def del_payment(request: Request, ext_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "approve extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        extract.approved = True
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/disapprove/{ext_id}")
def del_payment(request: Request, ext_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id,
                                                 Permission.type == "approve extracts").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    extract = db.query(Extract).filter(Extract.id == ext_id).first()
    if not extract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        extract.approved = False
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.get("/generate_pdf/{ext_id}")
def del_payment(request: Request, ext_id: int, is_history: bool, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permissions = db.query(Permission).filter(Permission.user_id == user_id).all()
        permission_types = [p.type for p in permissions]
        if "generate pdf" not in permission_types:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if is_history:
        extract = db.query(ExtractHistory).filter(ExtractHistory.id == ext_id).first()
        if not extract:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        categories = db.query(ExtractCategoryHistory).filter(ExtractCategoryHistory.extract_history_id == extract.id).all()
        category_ids = [c.id for c in categories]
        items = db.query(ExtractCategoryItemHistory).filter(ExtractCategoryItemHistory.extract_category_history_id.in_(category_ids)).all()

        taxes = db.query(ExtractTaxesHistory).filter(ExtractTaxesHistory.extract_history_id == extract.id).all()
        deductions = db.query(ExtractDeductionHistory).filter(ExtractDeductionHistory.extract_history_id == extract.id).all()
        payments = db.query(ExtractPreviouslyPaidHistory).filter(ExtractPreviouslyPaidHistory.extract_history_id == extract.id).all()
        items_by_cat = {}
        for item in items:
            items_by_cat.setdefault(item.extract_category_history_id, []).append(item)

    else:
        extract = db.query(Extract).filter(Extract.id == ext_id).first()
        if not extract:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        categories = db.query(ExtractCategory).filter(ExtractCategory.extract_id == extract.id).all()
        category_ids = [c.id for c in categories]
        items = db.query(ExtractCategoryItem).filter(ExtractCategoryItem.category_id.in_(category_ids)).all()

        taxes = db.query(ExtractTaxes).filter(ExtractTaxes.extract_id == extract.id).all()
        deductions = db.query(ExtractDeduction).filter(ExtractDeduction.extract_id == extract.id).all()
        payments = db.query(ExtractPreviouslyPaid).filter(ExtractPreviouslyPaid.extract_id == extract.id).all()
        items_by_cat = {}
        for item in items:
            items_by_cat.setdefault(item.category_id, []).append(item)

    try:
        pdf_buffer = generate_extract_pdf(extract, is_history, categories, items_by_cat, taxes, deductions, payments)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{extract.id}.pdf"}
    )