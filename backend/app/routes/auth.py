"""
GhostWatt - routes/auth.py
Authentication endpoints.

Security notes
- Passwords are verified ONLY against the stored bcrypt hash (no demo/master passwords).
- Failed logins are rate limited per client + account.
- Student sign-in is by mobile number + OTP; every number maps to its own student account,
  so students never share data. Demo mode accepts the fixed OTP 123456 (see core/config.py).
- Admin password reset is bound to the admin account that owns the verified phone number and
  the reset token can be used once.
"""
import secrets
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.phone import normalize_phone
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db import models
from app.schemas.auth import (
    AdminForgotVerifyRequest,
    AdminResetPasswordRequest,
    LoginRequest,
    OtpSendRequest,
    OtpSendResponse,
    StudentOtpVerifyRequest,
    TokenResponse,
    UserResponse,
)
from app.services import otp_store
from app.services.rate_limit import SlidingWindowLimiter

router = APIRouter()

# 8 failed password attempts per client+account per 5 minutes
login_limiter = SlidingWindowLimiter(max_events=8, window_seconds=300)
otp_verify_limiter = SlidingWindowLimiter(max_events=12, window_seconds=300)
_used_reset_tokens: set = set()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _user_response(user: models.User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        name=user.full_name or user.username,
        email=user.email,
        role=user.role,
        is_active=bool(user.is_active),
        data_source="simulated",
    )


def _token_for(user: models.User) -> TokenResponse:
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "email": user.email, "username": user.username}
    )
    return TokenResponse(access_token=token, token_type="bearer", user=_user_response(user), data_source="simulated")


def _identifier(payload: LoginRequest) -> str:
    return str(payload.username_or_email or payload.email or payload.username or "").strip()


def _authenticate(payload: LoginRequest, request: Request, db: Session, require_role: Optional[str] = None) -> models.User:
    identifier = _identifier(payload)
    if not identifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email is required")

    key = f"{_client_ip(request)}|{identifier.lower()}"
    wait = login_limiter.retry_after(key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed sign-in attempts. Try again in {wait} seconds.",
            headers={"Retry-After": str(wait)},
        )

    user = (
        db.query(models.User)
        .filter((models.User.email.ilike(identifier)) | (models.User.username.ilike(identifier)))
        .first()
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        login_limiter.record(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")
    if require_role and user.role != require_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Admin role required.")

    login_limiter.clear(key)
    return user


@router.post("/login", response_model=TokenResponse, summary="User login with JWT token issuance")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate username/email + password (bcrypt) and return a JWT bearer token."""
    return _token_for(_authenticate(payload, request, db))


@router.post("/admin/login", response_model=TokenResponse, summary="Admin login with email and password")
def admin_login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Admin-specific login route used by the frontend."""
    return _token_for(_authenticate(payload, request, db, require_role="admin"))


# ---------------------------------------------------------------------------
# Student mobile OTP flow
# ---------------------------------------------------------------------------
def _phone_or_422(raw: str) -> str:
    try:
        return normalize_phone(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _otp_error(exc: otp_store.OtpError) -> HTTPException:
    code = status.HTTP_429_TOO_MANY_REQUESTS if exc.code == "OTP_COOLDOWN" else status.HTTP_400_BAD_REQUEST
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
    return HTTPException(status_code=code, detail=exc.message, headers=headers)


@router.post("/student/otp/send", response_model=OtpSendResponse, summary="Send OTP to student phone")
def send_student_otp(payload: OtpSendRequest):
    phone = _phone_or_422(payload.phone)
    try:
        code, resend = otp_store.issue("student", phone, settings.demo_mode)
    except otp_store.OtpError as exc:
        raise _otp_error(exc)
    return OtpSendResponse(resend_after_seconds=resend, dev_otp=code if settings.demo_mode else None)


@router.post("/student/otp/verify", response_model=TokenResponse, summary="Verify student OTP and return JWT")
def verify_student_otp(payload: StudentOtpVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """Verify the OTP; the phone number identifies (or creates) that student's own account."""
    phone = _phone_or_422(payload.phone)
    key = f"{_client_ip(request)}|otp|{phone}"
    wait = otp_verify_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many attempts. Try again in {wait} seconds.")
    try:
        otp_store.verify("student", phone, payload.otp)
    except otp_store.OtpError as exc:
        otp_verify_limiter.record(key)
        raise _otp_error(exc)

    user = db.query(models.User).filter(models.User.phone == phone).first()
    if user is None:
        user = models.User(
            username=f"student{phone}",
            email=f"{phone}@students.ghostwatt.local",
            password_hash=hash_password(secrets.token_urlsafe(24)),  # OTP-only account: password unusable
            role="student",
            is_active=True,
            phone=phone,
            full_name=f"Student ••{phone[-4:]}",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.role != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This number belongs to an administrator. Use admin sign-in.")
    elif not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is deactivated")

    otp_verify_limiter.clear(key)
    return _token_for(user)


# ---------------------------------------------------------------------------
# Admin forgot-password flow (phone -> OTP -> new password)
# ---------------------------------------------------------------------------
@router.post("/admin/forgot-password/send-otp", response_model=OtpSendResponse, summary="Send reset OTP to admin phone")
def admin_forgot_send_otp(payload: OtpSendRequest, db: Session = Depends(get_db)):
    phone = _phone_or_422(payload.phone)
    admin = db.query(models.User).filter(models.User.phone == phone, models.User.role == "admin").first()
    try:
        if admin is not None:
            code, resend = otp_store.issue("admin_reset", phone, settings.demo_mode)
        else:
            # Same response shape for unknown numbers so the endpoint cannot be used to find admins.
            code, resend = (otp_store.DEMO_OTP, otp_store.RESEND_AFTER_SECONDS)
    except otp_store.OtpError as exc:
        raise _otp_error(exc)
    return OtpSendResponse(resend_after_seconds=resend, dev_otp=code if (settings.demo_mode and admin is not None) else None)


@router.post("/admin/forgot-password/verify-otp", summary="Verify reset OTP")
def admin_forgot_verify_otp(payload: AdminForgotVerifyRequest, request: Request, db: Session = Depends(get_db)):
    phone = _phone_or_422(payload.phone)
    key = f"{_client_ip(request)}|reset|{phone}"
    wait = otp_verify_limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many attempts. Try again in {wait} seconds.")
    admin = db.query(models.User).filter(models.User.phone == phone, models.User.role == "admin").first()
    try:
        if admin is None:
            raise otp_store.OtpError("OTP_INVALID", "Invalid or expired code. Request a new one.")
        otp_store.verify("admin_reset", phone, payload.otp)
    except otp_store.OtpError as exc:
        otp_verify_limiter.record(key)
        raise _otp_error(exc)

    reset_token = create_access_token(
        {"sub": str(admin.id), "purpose": "pwd_reset", "jti": uuid.uuid4().hex},
        expires_delta=timedelta(minutes=15),
    )
    return {"reset_token": reset_token}


@router.post("/admin/forgot-password/reset", summary="Reset admin password with reset token")
def admin_forgot_reset(payload: AdminResetPasswordRequest, db: Session = Depends(get_db)):
    claims = decode_access_token(payload.reset_token)
    if not claims or claims.get("purpose") != "pwd_reset" or not claims.get("jti"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset session")
    if claims["jti"] in _used_reset_tokens:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link was already used")

    try:
        admin_id = int(claims.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset session")
    admin = db.query(models.User).filter(models.User.id == admin_id, models.User.role == "admin").first()
    if admin is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset session")

    admin.password_hash = hash_password(payload.new_password)
    db.commit()
    _used_reset_tokens.add(claims["jti"])
    return {"message": "Password updated successfully", "data_source": "simulated"}


@router.get("/me", response_model=UserResponse, summary="Get currently authenticated user details")
def get_me(current_user: models.User = Depends(get_current_user)):
    """Return user profile for the current bearer token."""
    return _user_response(current_user)
