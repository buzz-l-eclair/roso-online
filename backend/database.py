import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Sur Render: DATABASE_URL est injecté automatiquement par le service Postgres
# défini dans render.yaml. En local (dev), fallback sur SQLite pour ne pas
# obliger à installer Postgres juste pour tester le squelette.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./roso_dev.db")

# Render fournit parfois une URL "postgres://" (ancien scheme) que SQLAlchemy
# 2.x refuse ; on la corrige vers "postgresql://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
