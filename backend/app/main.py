import os
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .db import engine, SessionLocal, SQLALCHEMY_DATABASE_URL
from .models import Base
from .config import settings
from fastapi.middleware.cors import CORSMiddleware
from .deps import get_store, Store
from .schemas import TodoIn, TodoOut
from .logic import normalize_title, validate_new_todo, compute_stats, filter_todos
from .seed import seed_if_empty
from dotenv import load_dotenv

load_dotenv(os.getenv("ENV_FILE", None))

app = FastAPI(title=os.getenv("APP_NAME", "tp05-api"))

origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Seed opcional en el primer arranque (no debe tumbar el proceso si falla)
if settings.SEED_ON_START.lower() == "true":
    try:
        with SessionLocal() as db:
            seed_if_empty(db)
    except Exception as e:
        print(f"[WARN] seed_on_start failed: {e}")


@app.post("/admin/seed")
def run_seed(x_seed_token: str = Header(default="")):
    if not settings.SEED_TOKEN or x_seed_token != settings.SEED_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    with SessionLocal() as db:
        result = seed_if_empty(db)
    return {"ok": True, "env": settings.ENV, **result}


@app.get("/")
def root():
    return {"status": "ok", "message": "tp05-api running"}


# --- Healthchecks ---
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    info = {"app": "ok"}
    code = 200
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        info["db"] = "ok"
    except OperationalError as e:
        info["db"] = "down"
        info["error"] = e.__class__.__name__
        code = 503
    except Exception as e:
        info["db"] = "down"
        info["error"] = e.__class__.__name__
        code = 503
    return JSONResponse(info, status_code=code)


# --- DEBUG ---
@app.get("/admin/debug")
def debug():
    # Deducción básica de la ruta de archivo a partir de la URL de SQLite
    db_url = SQLALCHEMY_DATABASE_URL
    db_path: str | None = None

    if db_url.startswith("sqlite:////"):
        # Ej: sqlite:////home/app.db  -> /home/app.db
        db_path = db_url.replace("sqlite:////", "/", 1)
    elif db_url.startswith("sqlite:///"):
        # Ej: sqlite:///./app.db      -> ./app.db
        db_path = db_url.replace("sqlite:///", "", 1)

    file_exists = os.path.exists(db_path) if db_path else False

    return {
        "env": settings.ENV,
        "db_url": db_url,
        "db_path": db_path,
        "db_file_exists": file_exists,
    }

@app.get("/admin/touch")
def touch():
    from .models import Todo
    with SessionLocal() as db:
        return {"count": db.query(Todo).count()}


# --- TODOs ---
@app.get("/api/todos", response_model=list[TodoOut])
def list_todos(store: Store = Depends(get_store)):
    return store.list()


@app.get("/api/todos/stats")
def todos_stats(store: Store = Depends(get_store)):
    todos = store.list()
    return compute_stats(todos)


@app.get("/api/todos/search", response_model=list[TodoOut])
def search_todos(
    q: str | None = None,
    done: bool | None = None,
    store: Store = Depends(get_store),
):
    todos = store.list()
    filtered = filter_todos(todos, done=done, text=q)
    return filtered


@app.patch("/api/todos/{todo_id}/toggle", response_model=TodoOut)
def toggle_todo(todo_id: int, store: Store = Depends(get_store)):
    """Invierte el estado done de un "todo".

    - 200 con el "todo" actualizado si existe.
    - 404 si no existe.
    """
    todo = store.toggle(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="todo not found")
    return todo


@app.post("/api/todos", response_model=TodoOut, status_code=201)
def create_todo(payload: TodoIn, store: Store = Depends(get_store)):
    normalized = normalize_title(payload.title)
    try:
        validate_new_todo(normalized, store.list())
    except ValueError as e:
        code = str(e)
        if code == "empty":
            raise HTTPException(status_code=400, detail="title must not be empty")
        if code == "duplicate":
            raise HTTPException(status_code=400, detail="title must be unique")
        raise

    todo = store.add(title=normalized, description=payload.description)
    return todo


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("API_PORT", 8080)))
