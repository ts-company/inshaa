from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.users_model import User
from app.models.permissions_model import Permission
from app.core.auth import validate_user
from app.database import get_db
from app.schemas.user import UserCreate, EditUser
from app.schemas.permissions import AddPerm
from app.config import BASE_DIR, preset_permissions

router = APIRouter(prefix="/users")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def get_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage users").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    current_users = db.query(User).filter(User.id != user_id).all()

    users = [
        {
            "id": u.id,
            "name": f"{u.first_name} {u.last_name}",
            "role": u.role,
            "is_active": u.is_active
        }
        for u in current_users
    ]
    return templates.TemplateResponse("users.html", {"request": request, "users": users})

@router.post("/add")
def add_user(request: Request, payload: UserCreate, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage users").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    available_roles = {"super_admin", "eng_admin", "acc_admin", "engineer", "accountant"}
    if payload.role not in available_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        new_user = User(
                first_name=payload.first_name,
                last_name=payload.last_name,
                username=payload.username,
                password=hash_password(payload.password),
                role=payload.role,
                is_active=True,
            )
        db.add(new_user)
        db.flush()
        for type in preset_permissions[payload.role]:
            db.add(Permission(user_id=new_user.id, type=type))

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}


@router.delete("/delete/{id}")
def del_user(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage users").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    to_be_deleted = db.query(User).filter(User.id == id).first()
    if not to_be_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        db.delete(to_be_deleted)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/activate/{id}")
def activate(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage users").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    to_be_activated = db.query(User).filter(User.id == id).first()
    if not to_be_activated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        to_be_activated.is_active = True
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/deactivate/{id}")
def deactivate(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage users").first()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    to_be_deactivated = db.query(User).filter(User.id == id).first()
    if not to_be_deactivated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        to_be_deactivated.is_active = False
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.get("/permissions/{id}")
def perms(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permissions = db.query(Permission).filter(Permission.user_id == id).all()
    return [
        {
            "id": p.id,
            "type": p.type,
        }
        for p in permissions
    ]

@router.post("/add_permission/{id}")
def add_perm(request: Request, id: int, payload: AddPerm, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    payload_type = payload.type.strip()
    if not payload_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        new_permission = Permission(user_id=id, type=payload_type)
        db.add(new_permission)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/del_permission/{perm_id}")
def del_prem(request: Request, perm_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        permission = db.query(Permission).filter(Permission.id == perm_id).first()
        db.delete(permission)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/edit_cred")
def get_projects(request: Request, payload: EditUser, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not payload.username and not payload.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    if payload.username:
        user.username = payload.username
    if payload.password:
        user.password = hash_password(payload.password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}