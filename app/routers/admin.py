from datetime import datetime, timezone

import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from .. import storage

from ..database import get_session
from ..models import (
    Availability, Booking, Category, Favorite, Order, Payment, Product, User,
)
from ..schemas import (
    AvailabilityIn, PaymentIn, ProductIn, ProductUpdate, StatusIn, StockIn,
)
from ..security import require_admin
from ..serializers import order_dict, product_public, user_public

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _names(session: Session) -> dict[str, str]:
    return {c.id: c.name for c in session.exec(select(Category)).all()}


# ---------- reset test activity (keeps products/categories/availability/admin) ----------
@router.post("/reset")
def reset_activity(session: Session = Depends(get_session)):
    """Clear all orders, payments, bookings, favourites and non-admin customers.
    Products, categories, availability and admin accounts are kept."""
    deleted = {}
    for model in (Payment, Order, Favorite, Booking):
        rows = session.exec(select(model)).all()
        deleted[model.__name__] = len(rows)
        for r in rows:
            session.delete(r)
    users = session.exec(select(User).where(User.role != "admin")).all()
    deleted["Customer"] = len(users)
    for u in users:
        session.delete(u)
    session.commit()
    return {"ok": True, "deleted": deleted}


# ---------- image upload ----------
_ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp"}
_MAX_UPLOAD = 5 * 1024 * 1024  # 5 MB


@router.post("/migrate-images")
def migrate_images(session: Session = Depends(get_session)):
    """One-time: move inline data-URL product images into object storage."""
    if not storage.is_configured():
        raise HTTPException(status_code=503, detail="Object storage is not configured.")
    migrated = 0
    for p in session.exec(select(Product)).all():
        if p.image and p.image.startswith("data:"):
            header, b64 = p.image.split(",", 1)
            content_type = header[len("data:"):].split(";")[0]
            p.image = storage.upload_image(base64.b64decode(b64), content_type)
            session.add(p)
            migrated += 1
    session.commit()
    return {"migrated": migrated}


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not storage.is_configured():
        raise HTTPException(status_code=503, detail="Object storage is not configured.")
    if file.content_type not in _ALLOWED_IMAGE:
        raise HTTPException(status_code=400, detail="Please upload a JPG, PNG or WEBP image.")
    data = await file.read()
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Image is too large (max 5 MB).")
    url = storage.upload_image(data, file.content_type)
    return {"url": url}


# ---------- products ----------
@router.get("/products")
def list_products(session: Session = Depends(get_session)):
    names = _names(session)
    rows = session.exec(select(Product).order_by(Product.id.desc())).all()
    return [product_public(p, names.get(p.category_id)) for p in rows]


@router.post("/products", status_code=201)
def create_product(body: ProductIn, session: Session = Depends(get_session)):
    if not session.get(Category, body.category_id):
        raise HTTPException(status_code=400, detail="Unknown category")
    p = Product(**body.model_dump())
    session.add(p)
    session.commit()
    session.refresh(p)
    return product_public(p, _names(session).get(p.category_id))


@router.put("/products/{product_id}")
def update_product(product_id: int, body: ProductUpdate, session: Session = Depends(get_session)):
    p = session.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    session.add(p)
    session.commit()
    session.refresh(p)
    return product_public(p, _names(session).get(p.category_id))


@router.patch("/products/{product_id}/stock")
def set_stock(product_id: int, body: StockIn, session: Session = Depends(get_session)):
    p = session.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    p.stock = max(0, body.stock)
    session.add(p)
    session.commit()
    return {"ok": True, "stock": p.stock}


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, session: Session = Depends(get_session)):
    p = session.get(Product, product_id)
    if p:
        session.delete(p)
        session.commit()


# ---------- categories ----------
@router.get("/categories")
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category).order_by(Category.order_index)).all()


# ---------- bookings ----------
def _booking_payload(b: Booking, session: Session) -> dict:
    phone = None
    if b.customer_id:
        u = session.get(User, b.customer_id)
        phone = u.phone if u else None
    return {**b.model_dump(), "customer_phone": phone}


@router.get("/bookings")
def list_bookings(session: Session = Depends(get_session)):
    rows = session.exec(select(Booking).order_by(Booking.date)).all()
    return [_booking_payload(b, session) for b in rows]


@router.patch("/bookings/{booking_id}")
def set_booking_status(booking_id: int, body: StatusIn, session: Session = Depends(get_session)):
    b = session.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    b.status = body.status
    session.add(b)
    session.commit()
    session.refresh(b)
    return _booking_payload(b, session)


@router.delete("/bookings/{booking_id}", status_code=204)
def delete_booking(booking_id: int, session: Session = Depends(get_session)):
    b = session.get(Booking, booking_id)
    if b:
        session.delete(b)
        session.commit()


# ---------- availability ----------
@router.put("/availability")
def update_availability(body: AvailabilityIn, session: Session = Depends(get_session)):
    av = session.get(Availability, 1)
    if not av:
        av = Availability(id=1)
    av.working_days = body.working_days
    av.open_hour = body.open_hour
    av.close_hour = body.close_hour
    av.blocked_dates = body.blocked_dates
    session.add(av)
    session.commit()
    return {
        "workingDays": av.working_days, "openHour": av.open_hour,
        "closeHour": av.close_hour, "blockedDates": av.blocked_dates,
    }


# ---------- orders + payments ----------
def _order_payload(o: Order, session: Session) -> dict:
    pays = session.exec(select(Payment).where(Payment.order_id == o.id)).all()
    return order_dict(o, pays)


@router.get("/orders")
def list_orders(session: Session = Depends(get_session)):
    orders = session.exec(select(Order).order_by(Order.created_at.desc())).all()
    return [_order_payload(o, session) for o in orders]


@router.patch("/orders/{order_id}")
def set_order_status(order_id: int, body: StatusIn, session: Session = Depends(get_session)):
    o = session.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o.status = body.status
    session.add(o)
    session.commit()
    return _order_payload(o, session)


@router.post("/orders/{order_id}/payments")
def add_payment(order_id: int, body: PaymentIn, session: Session = Depends(get_session)):
    o = session.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    session.add(Payment(order_id=order_id, amount=body.amount, method=body.method, note=body.note))
    session.commit()
    return _order_payload(o, session)


@router.delete("/orders/{order_id}/payments/{payment_id}")
def remove_payment(order_id: int, payment_id: int, session: Session = Depends(get_session)):
    pay = session.get(Payment, payment_id)
    if pay and pay.order_id == order_id:
        session.delete(pay)
        session.commit()
    o = session.get(Order, order_id)
    return _order_payload(o, session) if o else {"ok": True}


# ---------- customers ----------
@router.get("/customers")
def list_customers(session: Session = Depends(get_session)):
    customers = session.exec(select(User).where(User.role == "customer")).all()
    out = []
    for c in customers:
        orders = session.exec(select(Order).where(Order.customer_id == c.id)).all()
        spent = 0.0
        for o in orders:
            if o.status != "cancelled":
                spent += sum(p.amount for p in session.exec(select(Payment).where(Payment.order_id == o.id)).all())
        bookings = session.exec(select(Booking).where(Booking.customer_id == c.id)).all()
        out.append({**user_public(c), "orders": len(orders), "bookings": len(bookings), "spent": spent})
    out.sort(key=lambda x: x["spent"], reverse=True)
    return out


@router.get("/customers/{customer_id}")
def customer_detail(customer_id: int, session: Session = Depends(get_session)):
    c = session.get(User, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    orders = session.exec(select(Order).where(Order.customer_id == c.id)).all()
    bookings = session.exec(select(Booking).where(Booking.customer_id == c.id)).all()
    return {
        "customer": user_public(c),
        "orders": [_order_payload(o, session) for o in orders],
        "bookings": bookings,
    }


# ---------- analytics ----------
def _month_keys(n: int = 6) -> list[tuple[str, str]]:
    now = datetime.now(timezone.utc)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    out = []
    for i in range(n - 1, -1, -1):
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        out.append((f"{y}-{m}", months[m - 1]))
    return out


def _key(dt) -> str:
    return f"{dt.year}-{dt.month}"


@router.get("/analytics")
def analytics(session: Session = Depends(get_session)):
    buckets = _month_keys(6)
    keyset = {k for k, _ in buckets}

    payments = session.exec(select(Payment)).all()
    orders = {o.id: o for o in session.exec(select(Order)).all()}
    rev = {k: 0.0 for k in keyset}
    for p in payments:
        o = orders.get(p.order_id)
        if o and o.status != "cancelled":
            k = _key(p.ts)
            if k in rev:
                rev[k] += p.amount

    cust = {k: 0 for k in keyset}
    for u in session.exec(select(User).where(User.role == "customer")).all():
        k = _key(u.created_at)
        if k in cust:
            cust[k] += 1

    bk = {k: 0 for k in keyset}
    for b in session.exec(select(Booking)).all():
        k = f"{b.date.year}-{b.date.month}"
        if k in bk:
            bk[k] += 1

    # most ordered items by qty
    tally: dict[str, int] = {}
    for o in orders.values():
        if o.status == "cancelled":
            continue
        for it in o.items or []:
            tally[it["name"]] = tally.get(it["name"], 0) + it.get("qty", 1)
    top_items = sorted(
        ({"label": n, "value": v} for n, v in tally.items()), key=lambda x: x["value"], reverse=True
    )[:6]

    # top customers by amount paid
    spent: dict[str, float] = {}
    for o in orders.values():
        if o.status == "cancelled":
            continue
        paid = sum(p.amount for p in payments if p.order_id == o.id)
        spent[o.customer_name] = spent.get(o.customer_name, 0.0) + paid
    top_customers = sorted(
        ({"label": n, "value": v} for n, v in spent.items() if v > 0),
        key=lambda x: x["value"], reverse=True,
    )[:5]

    series = lambda d: [{"label": lbl, "value": d[k]} for k, lbl in buckets]
    return {
        "revenue": series(rev),
        "customers": series(cust),
        "bookings": series(bk),
        "topItems": top_items,
        "topCustomers": top_customers,
    }
