from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import account, admin, auth, public
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    yield


app = FastAPI(title="Aura by Bel API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(account.router)
app.include_router(admin.router)


@app.get("/", tags=["meta"])
def root():
    return {"name": "Aura by Bel API", "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health():
    return {"status": "healthy"}
