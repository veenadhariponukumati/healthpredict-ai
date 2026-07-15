"""Authentication routes: login, register, refresh, logout."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, DuplicateError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.repositories import UserRepository
from app.db.session import get_db_session
from app.middleware.auth import get_current_user
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserInfo,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    """Authenticate user and return JWT tokens."""
    repo = UserRepository(db)
    user = await repo.get_by_email(request.email)

    if not user or not verify_password(request.password, user.password_hash):
        raise AuthenticationError(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS",
        )

    if not user.is_active:
        raise AuthenticationError(
            message="Account is deactivated",
            code="ACCOUNT_DISABLED",
        )

    # Update last login
    await repo.update_last_login(str(user.id))

    # Generate tokens
    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = create_refresh_token(subject=str(user.id), role=user.role)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,  # 15 minutes in seconds
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user account."""
    repo = UserRepository(db)

    # Check for existing user
    existing = await repo.get_by_email(request.email)
    if existing:
        raise DuplicateError(
            message="Email already registered",
            resource_type="user",
            field="email",
            value=request.email,
        )

    # Create user
    user = await repo.create(
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
        is_active=True,
    )

    return RegisterResponse(
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
        message="User registered successfully. Awaiting admin activation.",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh an expired access token using a valid refresh token."""
    try:
        payload = decode_token(request.refresh_token)
    except Exception:
        raise AuthenticationError(
            message="Invalid or expired refresh token",
            code="INVALID_REFRESH_TOKEN",
        )

    if payload.get("type") != "refresh":
        raise AuthenticationError(
            message="Invalid token type. Use a refresh token.",
            code="INVALID_TOKEN_TYPE",
        )

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise AuthenticationError(
            message="Token missing required claims",
            code="INVALID_TOKEN_CLAIMS",
        )

    new_access = create_access_token(subject=user_id, role=role)
    new_refresh = create_refresh_token(subject=user_id, role=role)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=900,
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout the current user.

    In production, this would blacklist the token in Redis.
    For now, the client discards the token.
    """
    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Change the current user's password."""
    repo = UserRepository(db)
    user = await repo.get(current_user["user_id"])

    if not user or not verify_password(request.current_password, user.password_hash):
        raise AuthenticationError(
            message="Current password is incorrect",
            code="INVALID_PASSWORD",
        )

    await repo.update(
        current_user["user_id"],
        password_hash=hash_password(request.new_password),
    )

    return {"message": "Password changed successfully"}