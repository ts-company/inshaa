from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.database import engine, Base, get_db
from app.config import BASE_DIR
from app.utils import generate_url
from app.routes import login, home, dashboard, users, page, extracts, hr_management, backup

load_dotenv()

templates = Jinja2Templates(directory=BASE_DIR / "templates")

app = FastAPI()

app.mount("/static",StaticFiles(directory=BASE_DIR / "static"), name="static")

# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["inshaaminka.org"],
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
app.include_router(backup.router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):

    return templates.TemplateResponse("home.html", {"request": request, "hero_video_url": generate_url("hero", "video")})