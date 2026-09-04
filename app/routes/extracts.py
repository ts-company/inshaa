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

router = APIRouter(prefix="/system/extracts")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def get_projects(request: Request, db: Session = Depends(get_db)):

    projects = db.query(Project).all()
    projects_ids = [row.id for row in projects]

    medias = db.query(ProjectMedia).filter(ProjectMedia.project_id.in_(projects_ids)).all()
    medias_by_project = {}
    for m in medias:
        medias_by_project.setdefault(m.project_id, []).append(m)

    current_projects = [
        {
            "id": p.id,
            "title": p.title,
            "discription": p.description,
            "media_urls": [generate_url(m.public_id, m.resource_type) for m in medias_by_project.get(p.id, [])],
        }
        for p in projects
    ]
    return templates.TemplateResponse("extracts.html", {"request": request})