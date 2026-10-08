from sqlalchemy.orm import Session
from app.database import engine
from app.models.users_model import User
from app.core.auth import validate_user
from app.database import get_db
import subprocess
import tempfile
import os
import psycopg2
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

router = APIRouter(prefix="/system")

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = "db"

@router.get("/db_backup")
def download_database(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    dump_path = os.path.join(tempfile.gettempdir(), f"inshaa_{datetime.now():%Y%m%d_%H%M%S}.dump")

    result = subprocess.run(
        [
            "pg_dump",
            "-h", POSTGRES_HOST,
            "-U", POSTGRES_USER,
            "-d", POSTGRES_DB,
            "-F", "c",
            "-f", dump_path,
        ],
        env={**os.environ, "PGPASSWORD": POSTGRES_PASSWORD},
        capture_output=True,
    )

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="Backup failed")

    return FileResponse(
        dump_path,
        media_type="application/octet-stream",
        filename=os.path.basename(dump_path),
        background=BackgroundTask(os.remove, dump_path),
    )


@router.post("/db_restore")
async def restore_database(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if not file.filename.endswith(".dump"):
        raise HTTPException(status_code=400, detail="Expected a .dump file produced by pg_dump -F c")

    db.close()

    upload_path = os.path.join(tempfile.gettempdir(), f"restore_{datetime.now():%Y%m%d_%H%M%S}.dump")

    try:
        contents = await file.read()
        with open(upload_path, "wb") as f:
            f.write(contents)

        terminate_conn = psycopg2.connect(
            host=POSTGRES_HOST, user=POSTGRES_USER, password=POSTGRES_PASSWORD, dbname="postgres"
        )
        terminate_conn.autocommit = True
        with terminate_conn.cursor() as cur:
            cur.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid();
                """,
                (POSTGRES_DB,),
            )
        terminate_conn.close()

        result = subprocess.run(
            [
                "pg_restore",
                "-h", POSTGRES_HOST,
                "-U", POSTGRES_USER,
                "-d", POSTGRES_DB,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--single-transaction",
                upload_path,
            ],
            env={**os.environ, "PGPASSWORD": POSTGRES_PASSWORD},
            capture_output=True,
            timeout=300,
        )

        stderr_text = result.stderr.decode(errors="replace")
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Restore failed: {stderr_text}")

        engine.dispose()
        return {"success": True, "warnings": stderr_text or None}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Restore timed out after 5 minutes")
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)