from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.core.auth import validate_user
from app.models.extracts.contranctors import Contractor
from app.models.extracts.projects import Project
from app.database import get_db
from app.schemas.contractors import AddContractor, UpdateContractor
from app.schemas.projects import AddProject, UpdateProject

router = APIRouter(prefix="/codes")


@router.post("/contractors")
def get_contractors(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    contractors = db.query(Contractor).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "code": c.code
        }
        for c in contractors
    ]


@router.post("/contractor_add")
def add_contractor(request: Request, payload: AddContractor, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        new_contractor = Contractor(
            name = payload.name,
            code = payload.code
        )
        db.add(new_contractor)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}


@router.delete("/contractor_delete/{contractor_id}")
def delete_contractor(request: Request, contractor_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()

    if not user or user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
        db.delete(contractor)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}


@router.delete("/contractor_update/{contractor_id}")
def udpate_contractor(request: Request, payload: UpdateContractor, contractor_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()

    if not user or user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
        if payload.name is not None:
            contractor.name = payload.name
        if payload.code is not None:
            contractor.code = payload.code
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}


@router.post("/projects")
def get_projects(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    projects = db.query(Project).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "code": p.code
        }
        for p in projects
    ]


@router.post("/project_add")
def add_project(request: Request, payload: AddProject, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        new_project = Project(
            name=payload.name,
            code=payload.code
        )
        db.add(new_project)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}


@router.delete("/project_delete/{project_id}")
def delete_project(request: Request, project_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()

    if not user or user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        db.delete(project)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}


@router.delete("/project_update/{project_id}")
def update_project(request: Request, payload: UpdateProject, project_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()

    if not user or user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if payload.name is not None:
            project.name = payload.name
        if payload.code is not None:
            project.code = payload.code
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}