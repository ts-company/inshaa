from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.home.cv_categories_model import CvCategory
from app.models.home.cv_sub_categories import CvSubCategory
from app.models.home.home_projects_model import Project
from app.models.home.home_projects_medias_model import ProjectMedia
from app.database import get_db
from app.utils import generate_url
from app.config import BASE_DIR

router = APIRouter(prefix="/home")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/projects")
def get_projects(request: Request, db: Session = Depends(get_db)):

    projects = db.query(Project).order_by(Project.id.desc()).all()
    projects_ids = [row.id for row in projects]

    medias = db.query(ProjectMedia).filter(ProjectMedia.project_id.in_(projects_ids)).all()
    medias_by_project = {}
    for m in medias:
        medias_by_project.setdefault(m.project_id, []).append(m)

    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "media_urls": [generate_url(m.public_id, m.resource_type) for m in medias_by_project.get(p.id, [])],
        }
        for p in projects
    ]

@router.get("/cv")
def get_cv(request: Request, db: Session = Depends(get_db)):

    categories = db.query(CvCategory).order_by(CvCategory.id.desc()).all()
    categories_id = [row.id for row in categories]

    sub_cats = db.query(CvSubCategory).filter(CvSubCategory.category_id.in_(categories_id)).all()
    sub_by_cat = {}
    for sub in sub_cats:
        sub_by_cat.setdefault(sub.category_id, []).append(sub)

    return [
        {
            "id": c.id,
            "title": c.title,
            "sub_categories": [sub.text for sub in sub_by_cat.get(c.id, [])],
        }
        for c in categories
    ]