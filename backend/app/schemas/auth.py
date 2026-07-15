"""Auth schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    """User registration request body."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="viewer", pattern="^(admin|clinician|coordinator|viewer)$")


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """Public user information."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    """Login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class RegisterResponse(BaseModel):
    """Registration response."""

    user: UserInfo
    message: str = "User registered successfully"


class ChangePasswordRequest(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def passwords_differ(cls, new_password: str, info) -> str:
        if info.data.get("current_password") == new_password:
            raise ValueError("New password must differ from current password")
        return new_password