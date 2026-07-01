"""Response shaping — produces JSON the front-ends consume directly."""
from .models import Order, Payment, Product, User


def product_public(p: Product, category_name: str | None = None) -> dict:
    """Storefront-friendly product shape (camelCase where the UI expects it)."""
    return {
        "id": p.id,
        "name": p.name,
        "type": p.type,
        "category": p.category_id,
        "categoryName": category_name,
        "mode": p.mode,
        "status": p.status,
        "price": p.price,
        "compareAt": p.compare_at,
        "deposit": p.deposit,
        "variant": p.variant,
        "description": p.description,
        "alt": p.description,  # storefront image alt
        "badge": p.badge,
        "image": p.image,
        "stock": p.stock,
        "tags": p.tags or [],
        "options": p.options,
    }


def order_dict(o: Order, payments: list[Payment]) -> dict:
    paid = sum(p.amount for p in payments)
    return {
        "id": o.id,
        "customerId": o.customer_id,
        "customerName": o.customer_name,
        "status": o.status,
        "total": o.total,
        "paid": paid,
        "balance": max(0.0, o.total - paid),
        "items": o.items or [],
        "createdAt": o.created_at,
        "payments": [
            {"id": p.id, "amount": p.amount, "method": p.method, "note": p.note, "ts": p.ts}
            for p in sorted(payments, key=lambda x: x.ts)
        ],
    }


def user_public(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "role": u.role,
        "joined": u.created_at,
    }
