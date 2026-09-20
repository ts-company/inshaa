from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.database import engine, Base, get_db
from app.models.users_model import User
from app.models.permissions_model import Permission
from app.core.security import hash_password
from app.config import BASE_DIR, preset_permissions
from app.routes import login, home, dashboard, users, page, extracts, hr_management

load_dotenv()

templates = Jinja2Templates(directory=BASE_DIR / "templates")

app = FastAPI()

app.mount("/static",StaticFiles(directory=BASE_DIR / "static"), name="static")

# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login.router)
app.include_router(home.router)
app.include_router(dashboard.router)
app.include_router(page.router)
app.include_router(users.router)
app.include_router(extracts.router)
app.include_router(hr_management.router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):

    admin = db.query(User).filter(User.role == "super_admin").first()
    if not admin:
        new_admin = User(
            first_name="Admin",
            last_name="Admin",
            username="admin",
            password=hash_password("123"),
            role="super_admin",
            is_active=True
        )
        db.add(new_admin)
        db.flush()
        for perm in preset_permissions["super_admin"]:
            db.add(Permission(user_id=new_admin.id, type=perm))
        db.commit()

    return templates.TemplateResponse("home.html", {"request": request})