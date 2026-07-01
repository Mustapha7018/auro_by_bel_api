import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..config import settings
from ..database import get_session
from ..models import User
from ..schemas import GoogleAuthIn, LoginIn, PasswordChangeIn, RegisterIn
from ..security import (
    create_access_token, get_current_user, hash_password, verify_password,
)
from ..serializers import user_public

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> dict:
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user_public(user)}


@router.post("/register")
def register(body: RegisterIn, session: Session = Depends(get_session)):
    email = body.email.lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=400, detail="That email is already registered.")
    user = User(name=body.name, email=email, phone=body.phone,
                password_hash=hash_password(body.password), role="customer")
    session.add(user)
    session.commit()
    session.refresh(user)
    return _token_response(user)


@router.post("/login")
def login(body: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == body.email.lower())).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return _token_response(user)


@router.post("/google")
def google_sign_in(body: GoogleAuthIn, session: Session = Depends(get_session)):
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")

    # verify the ID token with Google
    from google.auth.transport import requests as g_requests
    from google.oauth2 import id_token

    try:
        info = id_token.verify_oauth2_token(
            body.credential, g_requests.Request(), settings.google_client_id
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token.")

    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Google account email not verified.")

    name = info.get("name") or info.get("given_name") or email.split("@")[0]

    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(24)),  # unusable password
            role="customer",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    return _token_response(user)


@router.post("/password")
def change_password(
    body: PasswordChangeIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")
    user.password_hash = hash_password(body.new_password)
    session.add(user)
    session.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_public(user)
