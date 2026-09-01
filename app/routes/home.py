from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.home_projects_model import Project
from app.models.home_projects_medias_model import ProjectMedia
from app.core.security import verify_password
from app.core.auth import create_access_token
from app.database import get_db
from app.schemas.user import UserLogin
from app.config import BASE_DIR

router = APIRouter("/home}")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/projects")
def login_page(request: Request, db: Session = Depends(get_db)):

    projects = db.query(Project).filter(Project.active == True).all()
    projects_ids = [row.id for row in projects]

    medias = db.query(ProjectMedia).filter(ProjectMedia.project_id.in_(projects_ids)).all()
    project_id_lookup = [
        {
            media.project_id: []
        }
        for media in medias
    ]

    return [
        {
            "id": p.id,
            "name": p.name,
            "discription": p.discription,
            "images": project_id_lookup[p.id]
        }
        for p in projects
    ]