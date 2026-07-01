# Aura by Bel — API

A small **FastAPI** backend that serves both the **storefront** (`../aura`) and the
**studio dashboard** (`../aura-dashboard`). SQLModel + SQLite for dev (swap to Postgres
via `DATABASE_URL`), JWT auth with bcrypt, seeded with data that mirrors both apps.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit JWT_SECRET etc.
uvicorn app.main:app --reload --port 8000
```

- Interactive docs: **http://localhost:8000/docs**
- The database (`aura.db`) is created and **seeded on first run** (delete the file to reset).

## Demo logins

| Role | Email | Password |
|------|-------|----------|
| Admin (Bel) | `bel@aurabybel.com` | `studio` |
| Customer | `ama.mensah@gmail.com` | `password` |

`POST /auth/login` returns `{ access_token, user }`. Send it as `Authorization: Bearer <token>`.

## Endpoints

**Auth** — `POST /auth/register`, `POST /auth/login`, `GET /auth/me`

**Public (storefront)**
- `GET /catalog` — categories with nested products (the whole storefront catalogue)
- `GET /products`, `GET /products/{id}`
- `GET /availability`
- `GET /bookings/slots?date=YYYY-MM-DD` — real open slots (working days, hours, blocked dates, minus taken)

**Customer** (`Bearer` token)
- `GET/PUT/DELETE /me/favorites[/{product_id}]`
- `GET /me/bookings`, `POST /me/bookings`
- `GET /me/orders`, `POST /me/orders` (checkout → order + first payment)

**Admin** (`role=admin`)
- Products: `GET/POST /admin/products`, `PUT/DELETE /admin/products/{id}`, `PATCH /admin/products/{id}/stock`
- `GET /admin/categories`
- Bookings: `GET /admin/bookings`, `PATCH /admin/bookings/{id}`
- `PUT /admin/availability`
- Orders: `GET /admin/orders`, `PATCH /admin/orders/{id}`, `POST /admin/orders/{id}/payments`, `DELETE /admin/orders/{id}/payments/{pid}`
- Customers: `GET /admin/customers`, `GET /admin/customers/{id}`
- `GET /admin/analytics` — revenue / new customers / bookings (6 months) + top items + top customers

## Data model

`users` (customer + admin) · `categories` · `products` (price, compare_at, status,
deposit, variant, options, stock, image, tags) · `availability` (singleton) ·
`bookings` · `orders` + `payments` · `favorites`.

Order totals are derived: `paid = Σ payments`, `balance = total − paid`.

## Wiring the front-ends (next step)

Both apps currently use local/mock data. To connect:

1. **Storefront** — replace `src/data/catalog.js` with a `fetch('/catalog')`; point the
   `auth`, `cart`/orders, `favorites`, and booking stores at `/auth`, `/me/*`,
   `/bookings/slots`.
2. **Dashboard** — replace the localStorage persist plugin with API calls to `/admin/*`;
   the store actions are the single place to do it.
3. Set `CORS_ORIGINS` to include the deployed front-end URLs.
4. **Auth:** the mocks (storefront Google, dashboard password) map onto `/auth/login`
   + the `role` field. For real Google sign-in, add an OAuth provider and issue the same
   JWT — the rest is unchanged.

## Deploy to Render

This repo ships a **`render.yaml` blueprint** that provisions a Postgres database
and a web service, wiring `DATABASE_URL` and generating a `JWT_SECRET` automatically.

1. Push this folder to its own Git repo (GitHub/GitLab).
2. Render dashboard → **New → Blueprint** → connect the repo → **Apply**.
   Render reads `render.yaml` and creates `aura-db` (Postgres) + `aura-api` (web).
3. When it's live you get a URL like `https://aura-api.onrender.com` — check `/health` and `/docs`.
4. **Custom subdomain:** in the `aura-api` service → **Settings → Custom Domains** → add
   `api.aurabybel.shop`. Render shows a **CNAME target** → add it in **Vercel → Domains →
   aurabybel.shop → DNS Records** as `Name: api`, `Type: CNAME`, `Value: <target>`.
   Render then provisions SSL.

Notes:
- Free tier web services **sleep after ~15 min idle** (first request after is slow) and
  free Postgres has size/retention limits — fine to start; upgrade when it matters.
- The Postgres driver (`psycopg`) installs only in prod (Python < 3.14); local dev uses SQLite.
- Rotate `JWT_SECRET` only intentionally — it invalidates existing tokens.
- Swap the `/images/*` paths for real uploaded URLs (object storage) as photos move off the repo.
- Add migrations (Alembic) once the schema settles.
