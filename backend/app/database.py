from sqlalchemy import create_engine  # type: ignore[reportMissingImports]
from sqlalchemy.orm import DeclarativeBase, sessionmaker  # type: ignore[reportMissingImports]
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
