import secrets
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

# unambiguous alphabet (no I/O/0/1/L) for human-readable references
_REF_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_ref() -> str:
    return "".join(secrets.choice(_REF_ALPHABET) for _ in range(6))


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    phone: str | None = None
    password_hash: str
    role: str = "customer"  # customer | admin
    created_at: datetime = Field(default_factory=utcnow)


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: str = Field(primary_key=True)  # slug, e.g. "wig-installation"
    name: str
    mode: str = "shop"  # shop | appointment
    blurb: str | None = None
    banner: str | None = None
    order_index: int = 0


class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    type: str | None = None
    category_id: str = Field(foreign_key="categories.id", index=True)
    mode: str = "shop"  # shop | appointment
    status: str = "instock"  # instock | preorder
    price: float = 0
    compare_at: float | None = None  # original price → "sale slash"
    deposit: float = 0
    variant: str | None = None  # short subtitle, e.g. "Body wave · 180%"
    description: str | None = None
    badge: str | None = None
    image: str | None = None
    stock: int | None = None
    tags: list = Field(default_factory=list, sa_column=Column(JSON))
    options: dict | None = Field(default=None, sa_column=Column(JSON))  # {label, values[]}
    created_at: datetime = Field(default_factory=utcnow)


class Availability(SQLModel, table=True):
    __tablename__ = "availability"
    id: int = Field(default=1, primary_key=True)  # singleton row
    working_days: list = Field(default_factory=lambda: [2, 3, 4, 5, 6], sa_column=Column(JSON))
    open_hour: int = 9
    close_hour: int = 18
    blocked_dates: list = Field(default_factory=list, sa_column=Column(JSON))


class Booking(SQLModel, table=True):
    __tablename__ = "bookings"
    id: int | None = Field(default=None, primary_key=True)
    customer_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    customer_name: str
    product_id: int | None = Field(default=None, foreign_key="products.id")
    service: str
    date: date
    time: str  # "11:00"
    deposit: float = 0
    status: str = "requested"  # requested | confirmed | completed | cancelled
    created_at: datetime = Field(default_factory=utcnow)


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    id: int | None = Field(default=None, primary_key=True)
    ref: str = Field(default_factory=gen_ref, index=True)  # public, non-sequential order code
    customer_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    customer_name: str
    status: str = "processing"  # processing | delivered | cancelled
    total: float = 0
    items: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    id: int | None = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    amount: float
    method: str = "Cash"  # Cash | Mobile Money | Bank transfer | Card
    note: str = ""
    ts: datetime = Field(default_factory=utcnow)


class Favorite(SQLModel, table=True):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_fav"),)
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    product_id: int = Field(foreign_key="products.id")
    created_at: datetime = Field(default_factory=utcnow)
