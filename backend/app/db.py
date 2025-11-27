import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Prioridad:
# 1) DATABASE_URL (nueva)
# 2) DB_URL       (legacy de TP05)
# 3) default local ./app.db
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "sqlite:///./app.db"

# Si es SQLite, nos aseguramos de que el directorio exista
db_path = None
if SQLALCHEMY_DATABASE_URL.startswith("sqlite:////"):
    # Ej: sqlite:////home/data/app.db -> /home/data/app.db
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:////", "/", 1)
elif SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
    # Ej: sqlite:///./app.db -> ./app.db
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "", 1)

if db_path:
    dir_path = os.path.dirname(db_path)
    # Evitamos intentar crear '' o '.'
    if dir_path and dir_path != ".":
        os.makedirs(dir_path, exist_ok=True)

connect_args: dict = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
