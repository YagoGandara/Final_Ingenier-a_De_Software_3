import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Prioridad:
# 1) DATABASE_URL (nueva)
# 2) DB_URL       (legacy de TP05)
# 3) default local ./app.db
SQLALCHEMY_DATABASE_URL = (
    os.getenv("DATABASE_URL") or
    os.getenv("DB_URL") or
    "sqlite:///./app.db"
)

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
