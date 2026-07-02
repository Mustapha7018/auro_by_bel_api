from sqlalchemy import inspect, text
from sqlmodel import SQLModel, Session, create_engine

from .config import settings
from .models import gen_ref


def _normalize(url: str) -> str:
    """Render/Heroku hand out `postgres://` or `postgresql://`; point both at
    the psycopg (v3) driver we install in production."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize(settings.database_url)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_order_ref()


def _ensure_order_ref() -> None:
    """Add the non-sequential `orders.ref` column to databases created before it
    existed, and backfill any rows that predate it. Safe to run on every boot."""
    insp = inspect(engine)
    if not insp.has_table("orders"):
        return
    if "ref" in {c["name"] for c in insp.get_columns("orders")}:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE orders ADD COLUMN ref VARCHAR"))
        rows = conn.execute(text("SELECT id FROM orders WHERE ref IS NULL")).fetchall()
        for (oid,) in rows:
            conn.execute(text("UPDATE orders SET ref = :r WHERE id = :id"), {"r": gen_ref(), "id": oid})


def get_session():
    with Session(engine) as session:
        yield session
