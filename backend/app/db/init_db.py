from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db.models import Base
from app.db.session import engine


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    if alembic_ini.exists():
        command.upgrade(Config(str(alembic_ini)), "head")
    else:
        Base.metadata.create_all(bind=engine)
