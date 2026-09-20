from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.hr.candidates import Candidate
from app.models.users_model import User
from app.models.permissions_model import Permission
from app.core.auth import validate_user
from app.database import get_db
from app.utils import generate_url, delete_file
from app.config import BASE_DIR

router = APIRouter(prefix="/system/hr_management")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def get_page(request: Request, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "hr management").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    candidates = db.query(Candidate).all()

    current_candidates = [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone_number": c.phone_number,
            "age": c.age,
            "picture_url": generate_url(c.picture_id, "/image"),
            "cv_url": generate_url(c.cv_id, "/image"),
        }
        for c in candidates
    ]
    return templates.TemplateResponse("hr_management.html", {"request": request, "candidates": current_candidates})


@router.delete("/del_candidate/{can_id}")
def del_candidate(request: Request, can_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "hr management").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    candidate = db.query(Candidate).filter(Candidate.id == can_id).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        db.delete(candidate)
        if candidate.picture_id is not None:
            delete_file(candidate.picture_id, "/image")
        if candidate.cv_id is not None:
            delete_file(candidate.cv_id, "/image")
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}