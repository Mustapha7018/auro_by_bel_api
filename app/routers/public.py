from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Availability, Booking, Category, GalleryItem, Product
from ..serializers import product_public
from ..slots import day_slots

router = APIRouter(tags=["public"])


@router.get("/gallery")
def gallery(session: Session = Depends(get_session)):
    """Bel's creations — newest first."""
    rows = session.exec(select(GalleryItem).order_by(GalleryItem.id.desc())).all()
    return [{"id": g.id, "kind": g.kind, "url": g.url} for g in rows]


def _category_names(session: Session) -> dict[str, str]:
    return {c.id: c.name for c in session.exec(select(Category)).all()}


@router.get("/catalog")
def catalog(session: Session = Depends(get_session)):
    """Categories with nested products — the storefront's whole catalogue."""
    cats = session.exec(select(Category).order_by(Category.order_index)).all()
    out = []
    for c in cats:
        prods = session.exec(
            select(Product).where(Product.category_id == c.id).order_by(Product.id)
        ).all()
        out.append({
            "id": c.id, "name": c.name, "mode": c.mode,
            "blurb": c.blurb, "banner": c.banner,
            "products": [product_public(p, c.name) for p in prods],
        })
    return out


@router.get("/products")
def list_products(
    mode: str | None = None,
    category: str | None = None,
    session: Session = Depends(get_session),
):
    q = select(Product)
    if mode:
        q = q.where(Product.mode == mode)
    if category:
        q = q.where(Product.category_id == category)
    names = _category_names(session)
    return [product_public(p, names.get(p.category_id)) for p in session.exec(q).all()]


@router.get("/products/{product_id}")
def get_product(product_id: int, session: Session = Depends(get_session)):
    p = session.get(Product, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    names = _category_names(session)
    return product_public(p, names.get(p.category_id))


@router.get("/availability")
def get_availability(session: Session = Depends(get_session)):
    av = session.get(Availability, 1) or Availability(id=1)
    return {
        "workingDays": av.working_days,
        "openHour": av.open_hour,
        "closeHour": av.close_hour,
        "blockedDates": av.blocked_dates,
    }


@router.get("/bookings/slots")
def booking_slots(
    date: date_type = Query(..., description="YYYY-MM-DD"),
    session: Session = Depends(get_session),
):
    av = session.get(Availability, 1) or Availability(id=1)
    taken = {
        b.time
        for b in session.exec(select(Booking).where(Booking.date == date)).all()
        if b.status != "cancelled"
    }
    return day_slots(av, date, taken)
