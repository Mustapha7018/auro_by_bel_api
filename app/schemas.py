from datetime import date

from pydantic import BaseModel, EmailStr


# ---- auth ----
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthIn(BaseModel):
    credential: str  # Google ID token from the Sign-in button


# ---- products (admin) ----
class ProductIn(BaseModel):
    name: str
    category_id: str
    type: str | None = None
    mode: str = "shop"
    status: str = "instock"
    price: float = 0
    compare_at: float | None = None
    deposit: float = 0
    variant: str | None = None
    description: str | None = None
    badge: str | None = None
    image: str | None = None
    stock: int | None = None
    tags: list[str] = []
    options: dict | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    category_id: str | None = None
    type: str | None = None
    mode: str | None = None
    status: str | None = None
    price: float | None = None
    compare_at: float | None = None
    deposit: float | None = None
    variant: str | None = None
    description: str | None = None
    badge: str | None = None
    image: str | None = None
    stock: int | None = None
    tags: list[str] | None = None
    options: dict | None = None


class StockIn(BaseModel):
    stock: int


# ---- bookings ----
class BookingIn(BaseModel):
    product_id: int | None = None
    service: str
    date: date
    time: str
    deposit: float = 0


class StatusIn(BaseModel):
    status: str


# ---- orders ----
class OrderItemIn(BaseModel):
    product_id: int | None = None
    name: str
    mode: str = "full"  # full | preorder
    length: str | None = None
    qty: int = 1
    price: float
    deposit: float = 0


class OrderIn(BaseModel):
    items: list[OrderItemIn]


class PaymentIn(BaseModel):
    amount: float
    method: str = "Cash"
    note: str = ""


# ---- availability ----
class AvailabilityIn(BaseModel):
    working_days: list[int]
    open_hour: int
    close_hour: int
    blocked_dates: list[str] = []
