"""
GhostWatt — app/core/deps.py
Reusable FastAPI dependency functions for database sessions and role-based access control.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import SessionLocal
from app.db import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# DB session
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Current user & Role dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Validate JWT access token and return the authenticated User model."""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = None
    try:
        user_id = int(sub)
        user = db.query(models.User).filter(models.User.id == user_id).first()
    except (ValueError, TypeError):
        pass

    if user is None:
        user = db.query(models.User).filter(
            (models.User.email == str(sub)) | (models.User.username == str(sub))
        ).first()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated",
        )

    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Enforce administrator permissions in backend dependencies."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required: operation forbidden for non-admin accounts",
        )
    return current_user


def require_student(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Enforce campus community role (student or admin)."""
    if current_user.role not in ("student", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: valid campus user required",
        )
    return current_user
