from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Availability, Booking, Category, Favorite, Order, Payment, Product, User,
)
from ..schemas import BookingIn, OrderIn
from ..security import get_current_user
from ..serializers import order_dict, product_public
from ..slots import day_slots

router = APIRouter(prefix="/me", tags=["account"])


# ---- favourites ----
@router.get("/favorites")
def my_favorites(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    favs = session.exec(select(Favorite).where(Favorite.user_id == user.id)).all()
    names = {c.id: c.name for c in session.exec(select(Category)).all()}
    out = []
    for f in favs:
        p = session.get(Product, f.product_id)
        if p:
            out.append(product_public(p, names.get(p.category_id)))
    return out


@router.put("/favorites/{product_id}")
def add_favorite(product_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not session.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    existing = session.exec(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.product_id == product_id)
    ).first()
    if not existing:
        session.add(Favorite(user_id=user.id, product_id=product_id))
        session.commit()
    return {"ok": True, "favorited": True}


@router.delete("/favorites/{product_id}")
def remove_favorite(product_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    fav = session.exec(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.product_id == product_id)
    ).first()
    if fav:
        session.delete(fav)
        session.commit()
    return {"ok": True, "favorited": False}


# ---- bookings ----
@router.get("/bookings")
def my_bookings(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    rows = session.exec(
        select(Booking).where(Booking.customer_id == user.id).order_by(Booking.date)
    ).all()
    return rows


@router.post("/bookings")
def request_booking(body: BookingIn, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    av = session.get(Availability, 1) or Availability(id=1)
    taken = {
        b.time for b in session.exec(select(Booking).where(Booking.date == body.date)).all()
        if b.status != "cancelled"
    }
    slot = next((s for s in day_slots(av, body.date, taken) if s["time"] == body.time), None)
    if not slot or not slot["available"]:
        raise HTTPException(status_code=409, detail="That time is no longer available.")

    booking = Booking(
        customer_id=user.id, customer_name=user.name, product_id=body.product_id,
        service=body.service, date=body.date, time=body.time,
        deposit=body.deposit, status="requested",
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)
    return booking


# ---- orders ----
@router.get("/orders")
def my_orders(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    orders = session.exec(
        select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())
    ).all()
    out = []
    for o in orders:
        pays = session.exec(select(Payment).where(Payment.order_id == o.id)).all()
        out.append(order_dict(o, pays))
    return out


@router.post("/orders")
def checkout(body: OrderIn, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not body.items:
        raise HTTPException(status_code=400, detail="Your bag is empty.")
    total = sum(i.price * i.qty for i in body.items)
    due_now = sum((i.price if i.mode == "full" else i.deposit) * i.qty for i in body.items)
    order = Order(
        customer_id=user.id, customer_name=user.name, status="processing", total=total,
        items=[{"name": i.name, "mode": i.mode, "length": i.length, "qty": i.qty, "price": i.price}
               for i in body.items],
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    payment = Payment(order_id=order.id, amount=due_now, method="Online", note="Checkout")
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return order_dict(order, [payment])
