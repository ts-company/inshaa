from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.cv_categories_model import CvCategory
from app.models.cv_sub_categories import CvSubCategory
from app.models.users_model import User
from app.models.home_projects_model import Project
from app.models.home_projects_medias_model import ProjectMedia
from app.models.permissions_model import Permission
from app.core.auth import validate_user
from app.database import get_db
from app.utils import generate_url, upload_file, delete_file
from app.schemas.cv import AddCategory, EditCategory
from app.config import BASE_DIR
from typing import List

router = APIRouter(prefix="/page")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def get_page(request: Request, db: Session = Depends(get_db)):

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
    return templates.TemplateResponse("manage_page.html", {"request": request, "projects": current_projects})

@router.post("/add_project")
def add_project(request: Request, title: str = Form(...),
                description: str = Form(...),
                files: List[UploadFile] = File(default=[]),
                types: List[str] = Form(default=[]),
                db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage page").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if len(files) != len(types):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    valid_types = {"image", "video"}
    if any(t not in valid_types for t in types):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        new_project = Project(
            title=title,
            description=description
        )
        db.add(new_project)
        db.flush()
        for file, type in zip(files, types):
            public_id = upload_file(file, "media")
            project_media = ProjectMedia(project_id=new_project.id, public_id=public_id, resource_type=type)
            db.add(project_media)
        db.commit()
    except RuntimeError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_project/{project_id}")
def del_project(request: Request,
                project_id: int,
                db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage page").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    project_medias = db.query(ProjectMedia).filter(ProjectMedia.project_id == project.id).all()

    try:
        for media in project_medias:
            delete_file(media.public_id, media.resource_type)
            db.delete(media)
        db.delete(project)
        db.commit()
    except RuntimeError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/add_category")
def add_cat(request: Request,
                payload: AddCategory,
                db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage page").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if len(payload.sub_categories) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        new_category = CvCategory(title=payload.title)
        db.add(new_category)
        db.flush()
        for sub_cat in payload.sub_categories:
            new_sub_category = CvSubCategory(category_id=new_category.id, text=sub_cat.text)
            db.add(new_sub_category)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_category/{cat_id}")
def del_cat(request: Request,
                cat_id: int,
                db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage page").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    category = db.query(CvCategory).filter(CvCategory.id == cat_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        db.delete(category)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/edit_category/{cat_id}")
def del_cat(request: Request,
                cat_id: int,
                payload: EditCategory,
                db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage page").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    category = db.query(CvCategory).filter(CvCategory.id == cat_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if len(payload.sub_categories) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    existing_sub_categories = db.query(CvSubCategory).filter(CvSubCategory.category_id == category.id).all()

    try:
        for sub in existing_sub_categories:
            db.delete(sub)
        for new_sub in payload.sub_categories:
            db.add(CvSubCategory(category_id=category.id, text=new_sub.text))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.get("/categories")
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