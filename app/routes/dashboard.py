from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File, Form
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.home_projects_model import Project
from app.models.home_projects_medias_model import ProjectMedia
from app.models.permissions_model import Permission
from app.core.auth import validate_user
from app.database import get_db
from app.utils import generate_url, upload_file
from app.config import BASE_DIR
from typing import List

router = APIRouter(prefix="/system/dashboard")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def get_projects(request: Request, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    permissions = db.query(Permission).filter(Permission.user_id == user_id).all()
    perm_types = [row.type for row in permissions]

    return templates.TemplateResponse("dashboard.html", {"request": request, "permissions": perm_types, "user": f"{user.first_name} {user.last_name}"})