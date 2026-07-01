from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import User
from ..schemas import LoginIn, RegisterIn
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


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_public(user)
