"""
GhostWatt - schemas/auth.py
Pydantic schemas for authentication requests and responses.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username_or_email: Optional[str] = Field(None, max_length=200, description="Username or Email address")
    email: Optional[str] = Field(None, max_length=200, description="Direct Email address")
    username: Optional[str] = Field(None, max_length=200, description="Direct Username")
    password: str = Field(..., min_length=1, max_length=200, description="User password")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    name: Optional[str] = None
    data_source: str = "simulated"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    data_source: str = "simulated"


class OtpSendRequest(BaseModel):
    phone: str = Field(..., max_length=20)


class OtpSendResponse(BaseModel):
    resend_after_seconds: int = 30
    dev_otp: Optional[str] = None  # only present in DEMO_MODE
    data_source: str = "simulated"


class StudentOtpVerifyRequest(BaseModel):
    phone: str = Field(..., max_length=20)
    otp: str = Field(..., min_length=4, max_length=8)


class AdminForgotVerifyRequest(BaseModel):
    phone: str = Field(..., max_length=20)
    otp: str = Field(..., min_length=4, max_length=8)


class AdminResetPasswordRequest(BaseModel):
    reset_token: str = Field(..., max_length=2000)
    new_password: str = Field(..., min_length=8, max_length=128)
