from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.core.security import verify_password
from app.core.auth import create_access_token
from app.database import get_db
from app.schemas.user import UserLogin
from app.config import BASE_DIR

router = APIRouter(prefix="/system")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(userlogin: UserLogin,
                db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == userlogin.username).first()
    if not user or not verify_password(userlogin.password, user.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    response = JSONResponse({"role": user.role})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/"
    )
    # for deployment
    # samesite = "none",
    # secure = True,

    return response

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/system/")
    response.delete_cookie(
        key="access_token",
        path="/",
    )
    return response