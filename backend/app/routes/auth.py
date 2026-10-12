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
    query_filter = (models.User.email.ilike(identifier_str)) | (models.User.username.ilike(identifier_str))
    if identifier_str.lower() in ("admin@ecocampus.demo", "admin@ghostwatt.demo"):
        query_filter = (models.User.role == "admin")

    user = db.query(models.User).filter(query_filter).first()

    valid_password = False
    if user:
        if verify_password(payload.password, user.password_hash):
            valid_password = True
        elif payload.password in ("admin123", "demo") and user.role == "admin":
            valid_password = True

    if user is None or not valid_password:
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
            name="Demo Admin" if user.role == "admin" else "Demo Student",
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            data_source="simulated",
        ),
        data_source="simulated",
    )


@router.post("/admin/login", response_model=TokenResponse, summary="Admin login with email and password")
def admin_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Admin-specific login route used by frontend."""
    email_or_user = payload.email or payload.username_or_email or payload.username
    if not email_or_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")

    email_clean = str(email_or_user).strip()
    # Support both demo domain variations
    query_filter = (models.User.email.ilike(email_clean)) | (models.User.username.ilike(email_clean))
    if email_clean.lower() in ("admin@ecocampus.demo", "admin@ghostwatt.demo"):
        query_filter = (models.User.role == "admin")

    user = db.query(models.User).filter(query_filter).first()
    valid_password = False
    if user:
        if verify_password(payload.password, user.password_hash):
            valid_password = True
        elif payload.password in ("admin123", "demo"):
            valid_password = True

    if user is None or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. For demo: admin@ghostwatt.demo / admin123",
        )

    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Admin role required.")

    token = create_access_token(
        data={"sub": str(user.id), "role": "admin", "email": user.email, "username": user.username}
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            name="Demo Admin",
            email=user.email,
            role="admin",
            is_active=user.is_active,
            data_source="simulated",
        ),
        data_source="simulated",
    )


# ---------------------------------------------------------------------------
# Student Mobile OTP Flow
# ---------------------------------------------------------------------------
@router.post("/student/otp/send", summary="Send OTP to student phone")
def send_student_otp(payload: dict):
    """Generates and returns demo OTP for student mobile verification."""
    return {
        "resend_after_seconds": 30,
        "dev_otp": "123456",
        "data_source": "simulated",
    }


@router.post("/student/otp/verify", response_model=TokenResponse, summary="Verify student OTP and return JWT")
def verify_student_otp(payload: dict, db: Session = Depends(get_db)):
    """Verifies OTP and issues real JWT token for student."""
    otp = str(payload.get("otp", "")).strip()
    if otp != "123456":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP. Use demo code 123456.")

    # Find the seeded student user
    student = db.query(models.User).filter(models.User.role == "student").first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student account not found")

    token = create_access_token(
        data={"sub": str(student.id), "role": "student", "email": student.email, "username": student.username}
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=student.id,
            username=student.username,
            name="Demo Student",
            email=student.email,
            role="student",
            is_active=student.is_active,
            data_source="simulated",
        ),
        data_source="simulated",
    )


# ---------------------------------------------------------------------------
# Admin Forgot Password OTP Flow
# ---------------------------------------------------------------------------
@router.post("/admin/forgot-password/send-otp", summary="Send reset OTP to admin phone")
def admin_forgot_send_otp(payload: dict):
    return {
        "resend_after_seconds": 30,
        "dev_otp": "123456",
        "data_source": "simulated",
    }


@router.post("/admin/forgot-password/verify-otp", summary="Verify reset OTP")
def admin_forgot_verify_otp(payload: dict):
    otp = str(payload.get("otp", "")).strip()
    if otp != "123456":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP. Use demo code 123456.")
    from datetime import timedelta
    reset_token = create_access_token({"sub": "admin_reset", "purpose": "pwd_reset"}, expires_delta=timedelta(minutes=15))
    return {"reset_token": reset_token}


@router.post("/admin/forgot-password/reset", summary="Reset admin password with reset token")
def admin_forgot_reset(payload: dict, db: Session = Depends(get_db)):
    from app.core.security import decode_access_token, hash_password
    token = payload.get("reset_token", "")
    new_password = payload.get("new_password", "")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 6 characters")

    claims = decode_access_token(token)
    if not claims or claims.get("purpose") != "pwd_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset session")

    admin_user = db.query(models.User).filter(models.User.role == "admin").first()
    if admin_user:
        admin_user.password_hash = hash_password(new_password)
        db.commit()
    return {"message": "Password updated successfully", "data_source": "simulated"}


@router.get("/me", response_model=UserResponse, summary="Get currently authenticated user details")
def get_me(current_user: models.User = Depends(get_current_user)):
    """Return user profile for the current bearer token."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        name="Demo Admin" if current_user.role == "admin" else "Demo Student",
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        data_source="simulated",
    )

