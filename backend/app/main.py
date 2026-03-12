from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import create_token, decode_token, hash_password, verify_password
from .database import Base, SessionLocal, engine
from .models import Attempt, Task, User
from .seed import bootstrap_training_db

app = FastAPI(title="SQL Trainer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"


class AuthIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=4, max_length=64)


class QueryIn(BaseModel):
    query: str = Field(min_length=1)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ").strip()
    subject = decode_token(token)
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.username == subject).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


FORBIDDEN_PATTERN = re.compile(r"\b(drop|delete|update|insert|alter|truncate|create|attach|pragma)\b", re.I)


def validate_sql(query: str) -> None:
    cleaned = query.strip().strip(";")
    if not cleaned.lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    if FORBIDDEN_PATTERN.search(cleaned):
        raise HTTPException(status_code=400, detail="Forbidden SQL command detected")


def run_select(db: Session, query: str) -> dict[str, Any]:
    validate_sql(query)
    try:
        result = db.execute(text(query))
        rows = [dict(row._mapping) for row in result]
        return {"columns": list(result.keys()), "rows": rows}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"SQL error: {exc}") from exc


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_training_db(db)


@app.post("/api/auth/register")
def register(payload: AuthIn, db: Session = Depends(get_db)) -> dict[str, str]:
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    token = create_token(user.username)
    return {"token": token}


@app.post("/api/auth/login")
def login(payload: AuthIn, db: Session = Depends(get_db)) -> dict[str, str]:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.username)
    return {"token": token}


@app.get("/api/tasks")
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    tasks = db.query(Task).order_by(Task.id).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "difficulty": t.difficulty,
            "topic": t.topic,
        }
        for t in tasks
    ]


@app.get("/api/tasks/{task_id}")
def get_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "difficulty": task.difficulty,
        "topic": task.topic,
    }


@app.get("/api/schema")
def schema(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, list[dict[str, str]]]:
    table_names = ["groups", "students", "teachers", "courses", "grades"]
    output: dict[str, list[dict[str, str]]] = {}
    for table in table_names:
        rows = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
        output[table] = [{"name": r[1], "type": r[2]} for r in rows]
    return output


@app.post("/api/sql/execute")
def execute_sql(payload: QueryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    return run_select(db, payload.query)


@app.post("/api/tasks/{task_id}/check")
def check_task(task_id: int, payload: QueryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user_result = run_select(db, payload.query)
    expected_result = run_select(db, task.expected_query)

    is_correct = user_result["rows"] == expected_result["rows"] and user_result["columns"] == expected_result["columns"]

    attempt = Attempt(user_id=user.id, task_id=task_id, query=payload.query, is_correct=is_correct)
    db.add(attempt)
    db.commit()

    return {
        "is_correct": is_correct,
        "message": "Верно!" if is_correct else "Неверно, попробуйте ещё раз.",
        "result": user_result,
    }


@app.get("/api/progress")
def progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    attempts = db.query(Attempt).filter(Attempt.user_id == user.id).order_by(Attempt.created_at.desc()).all()
    total = len(attempts)
    correct = sum(1 for x in attempts if x.is_correct)
    solved_task_ids = {x.task_id for x in attempts if x.is_correct}
    return {
        "solved_tasks": len(solved_task_ids),
        "attempts": total,
        "success_rate": round((correct / total) * 100, 2) if total else 0,
        "history": [
            {
                "task_id": x.task_id,
                "is_correct": x.is_correct,
                "created_at": x.created_at.isoformat(),
            }
            for x in attempts[:20]
        ],
    }


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
