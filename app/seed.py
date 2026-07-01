"""Idempotent seed — runs once when the database is empty. Mirrors the
storefront catalogue and the dashboard's demo data so both apps have something
real to talk to."""
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from .database import engine
from .models import (
    Availability, Booking, Category, Favorite, Order, Payment, Product, User,
)
from .security import hash_password


def _day(offset: int) -> date:
    return date.today() + timedelta(days=offset)


CATEGORIES = [
    ("wig-installation", "Wig Installation", "appointment", "Scalp-melting installs finished to your hairline.", "/images/img2.jpg"),
    ("wig-making", "Wig Making", "shop", "Hand-built units, made to your measurements.", "/images/img5.jpg"),
    ("revamping", "Revamping", "appointment", "Tired units brought back to a salon-fresh finish.", "/images/img7.jpg"),
    ("pedicure", "Pedicure", "appointment", "Restoring soaks and a flawless finish.", "/images/p2.jpg"),
    ("nails", "Nails", "appointment", "Sculpted, structured and sealed to last.", "/images/nail2.jpg"),
    ("lash-extensions", "Lash Extensions", "appointment", "Seven signature sets, mapped to your eye shape.", "/images/wispy.jpg"),
    ("microblading", "Microblading", "appointment", "Semi-permanent brows mapped to your bone structure.", "/images/ombre_brows.jpg"),
    ("piercing", "Piercing", "appointment", "Precise placement, sterile single-use needles.", "/images/ear2.jpg"),
    ("retail", "Wigs & Bundles", "shop", "Single-donor raw hair and ready-to-wear units, shipped worldwide.", "/images/img4.jpg"),
]

# (category_id, name, type, mode, status, price, compare_at, deposit, variant, image, badge, stock, options)
PRODUCTS = [
    ("wig-installation", "Frontal Install", "Other", "appointment", "instock", 200, None, 70, "13×4 / 13×6 lace", "/images/install-frontal.jpg", "Popular", None, None),
    ("wig-installation", "Closure Install", "Other", "appointment", "instock", 150, None, 50, "4×4 / 5×5 lace", "/images/install-closure.jpg", None, None, None),
    ("wig-installation", "360 Install", "Other", "appointment", "instock", 250, None, 80, "Full perimeter", "/images/install-360.jpg", None, None, None),

    ("wig-making", "Frontal Unit", "Wig", "shop", "preorder", 850, None, 300, "Made to order", "/images/img1.jpg", "Made to order", 0, {"label": "Density", "values": ["150%", "180%", "200%"]}),
    ("wig-making", "Full Lace Unit", "Wig", "shop", "preorder", 1500, None, 500, "Hand-ventilated", "/images/img3.jpg", "Premium", 0, {"label": "Density", "values": ["180%", "200%"]}),

    ("revamping", "Wash & Restyle", "Other", "appointment", "instock", 80, None, 30, "Detangle & set", "/images/img2.jpg", None, None, None),
    ("revamping", "Deep Restore", "Other", "appointment", "instock", 150, None, 50, "Mask & revive", "/images/img6.jpg", "Popular", None, None),

    ("pedicure", "Classic Pedicure", "Pedicure", "appointment", "instock", 80, None, 25, "Soak, file & polish", "/images/p1.webp", None, None, None),
    ("pedicure", "Luxury Spa Pedicure", "Pedicure", "appointment", "instock", 200, None, 60, "Scrub, mask & massage", "/images/p3.jpg", "Popular", None, None),

    ("nails", "Builder Gel Full Set", "Nails", "appointment", "instock", 150, None, 50, "Natural overlay", "/images/nail1.jpg", "Popular", None, None),
    ("nails", "Acrylic Full Set", "Nails", "appointment", "instock", 180, None, 60, "Sculpted extension", "/images/nail2.jpg", None, None, None),
    ("nails", "Nail Art Set", "Nails", "appointment", "instock", 220, None, 70, "Custom design", "/images/nail4.png", "Custom", None, None),

    ("lash-extensions", "Classic Set", "Lashes", "appointment", "instock", 150, None, 50, "1:1 natural", "/images/classic_eye_lash.jpg", None, None, None),
    ("lash-extensions", "Volume Set", "Lashes", "appointment", "instock", 250, 300, 80, "Handmade fans", "/images/volume.webp", "Sale", None, None),
    ("lash-extensions", "Wispy Set", "Lashes", "appointment", "instock", 230, None, 70, "Textured & fluttery", "/images/wispy.jpg", "Popular", None, None),

    ("microblading", "Microblading", "Brows", "appointment", "instock", 600, None, 200, "Hair strokes", "/images/microblading.jpg", "Incl. touch-up", None, None),
    ("microblading", "Ombré Powder Brows", "Brows", "appointment", "instock", 800, None, 250, "Soft gradient", "/images/ombre_brows.jpg", "Popular", None, None),

    ("piercing", "Nostril Piercing", "Piercing", "appointment", "instock", 120, None, 40, "Stud or hoop", "/images/nose1.webp", None, None, None),
    ("piercing", "Belly Piercing", "Piercing", "appointment", "instock", 180, None, 60, "Navel · jewellery incl.", "/images/belly1.jpg", "Popular", None, None),
    ("piercing", "Ear Piercing", "Piercing", "appointment", "instock", 100, None, 30, "Lobe to helix", "/images/ear1.jpg", None, None, None),

    ("retail", "Raw SDD Bundles", "Bundle", "shop", "instock", 700, None, 250, "Straight · natural black", "/images/img1.jpg", "Best seller", 14, {"label": "Length", "values": ['16"', '18"', '20"', '22"', '24"']}),
    ("retail", "HD Lace Frontal Wig", "Wig", "shop", "instock", 2000, 2400, 700, "Body wave · 180%", "/images/img4.jpg", None, 6, {"label": "Length", "values": ['18"', '20"', '22"', '26"']}),
    ("retail", "Glueless 5×5 Closure Wig", "Wig", "shop", "instock", 1800, None, 600, "Deep curl · 200%", "/images/img3.jpg", "Low stock", 2, {"label": "Length", "values": ['16"', '18"', '20"']}),
    ("retail", "Coloured Pixie Unit", "Wig", "shop", "preorder", 1200, None, 400, "Honey blonde · pre-styled", "/images/img8.jpg", "Made to order", 0, {"label": "Length", "values": ['8"', '10"']}),
]


def seed() -> None:
    with Session(engine) as s:
        if s.exec(select(User)).first():
            return  # already seeded

        # --- admin only (no demo customers/bookings/orders) ---
        s.add(User(name="Bel", email="bel@aurabybel.com", phone="024 000 0000",
                   password_hash=hash_password("studio"), role="admin"))
        s.commit()

        # --- categories ---
        for i, (cid, name, mode, blurb, banner) in enumerate(CATEGORIES):
            s.add(Category(id=cid, name=name, mode=mode, blurb=blurb, banner=banner, order_index=i))
        s.commit()

        # --- products ---
        for (cat, name, typ, mode, status, price, comp, dep, variant, image, badge, stock, options) in PRODUCTS:
            s.add(Product(
                name=name, type=typ, category_id=cat, mode=mode, status=status,
                price=price, compare_at=comp, deposit=dep, variant=variant,
                image=image, badge=badge, stock=stock, options=options,
                description=f"{name} — {variant}." if variant else name,
                tags=[t for t in (typ.lower() if typ else "", status) if t],
            ))
        s.commit()

        # --- availability ---
        s.add(Availability(id=1))
        s.commit()


def _dt(offset_days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=offset_days)
