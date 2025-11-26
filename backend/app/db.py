import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Si viene DATABASE_URL por entorno, la usamos.
# Si no, mantenemos el comportamiento actual: sqlite:///./app.db
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db",
)

# Para SQLite necesitamos el connect_args, para otros motores no
connect_args = {}
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
