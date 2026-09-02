from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.home_projects_model import Project
from app.models.home_projects_medias_model import ProjectMedia
from app.models.permissions_model import Permission
from app.core.auth import validate_user
from app.database import get_db
from app.utils import generate_url, upload_file, delete_file
from app.config import BASE_DIR
from typing import List

router = APIRouter(prefix="/engineering")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def get_projects(request: Request, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role not in ("super_admin", "eng_admin", "engineer"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return templates.TemplateResponse("engineering_dashboard.html", {"request": request, "permissions": current_projects})