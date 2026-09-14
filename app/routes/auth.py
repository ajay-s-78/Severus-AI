from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from app.database.database import get_connection
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(...)
    password: str = Field(..., min_length=6)
    role: Optional[str] = "user"


class LoginSchema(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    status: str
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


@router.post("/register", response_model=TokenResponse)
def register_user(payload: RegisterSchema):
    conn = get_connection()
    cursor = conn.cursor()

    # Check if username or email exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (payload.username, payload.email))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered."
        )

    role = payload.role if payload.role in ["user", "admin"] else "user"
    hashed_pwd = hash_password(payload.password)

    cursor.execute(
        "INSERT INTO users (username, email, hashed_password, role) VALUES (?, ?, ?, ?)",
        (payload.username, payload.email, hashed_pwd, role)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    user_data = {
        "user_id": user_id,
        "username": payload.username,
        "email": payload.email,
        "role": role,
        "sub": str(user_id)
    }

    access_token = create_access_token(user_data)

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": payload.username,
            "email": payload.email,
            "role": role
        }
    }


@router.post("/login", response_model=TokenResponse)
def login_user(payload: LoginSchema):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, email, hashed_password, role FROM users WHERE username = ? OR email = ?", (payload.username, payload.username))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = {
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "sub": str(user["id"])
    }

    access_token = create_access_token(user_data)

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    }


@router.get("/me")
def get_user_profile(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "user": current_user
    }


@router.post("/logout")
def logout_user():
    return {
        "status": "success",
        "message": "Logged out successfully."
    }
