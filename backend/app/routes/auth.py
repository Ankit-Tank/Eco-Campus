"""
GhostWatt — routes/auth.py
Authentication endpoints: login and authenticated user profile.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.security import verify_password, create_access_token
from app.db import models
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="User login with JWT token issuance")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user credentials (email or username + password) using bcrypt.
    Returns JWT bearer token and user role metadata.
    """
    identifier = payload.username_or_email or payload.email or payload.username
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is required",
        )

    identifier_str = str(identifier).strip()
    user = db.query(models.User).filter(
        (models.User.email.ilike(identifier_str)) | (models.User.username.ilike(identifier_str))
    ).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "email": user.email, "username": user.username}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            data_source="simulated",
        ),
        data_source="simulated",
    )


@router.get("/me", response_model=UserResponse, summary="Get currently authenticated user details")
def get_me(current_user: models.User = Depends(get_current_user)):
    """Return user profile for the current bearer token."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        data_source="simulated",
    )
