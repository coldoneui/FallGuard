# User Authentication
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import query_one
from app.security import verify_password, create_access_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    """Used by login.html"""
    user = query_one("SELECT * FROM users WHERE email = %s", (body.email,))

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token({"id": user["id"], "email": user["email"]})

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "initials": user["initials"],
        },
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    """Restores session / populates settings.html profile card"""
    user = query_one(
        "SELECT id, name, email, role, initials FROM users WHERE id = %s",
        (current_user["id"],),
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user
