"""Repository for User model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User CRUD operations."""

    def __init__(self, db) -> None:
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email address."""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all active users."""
        return await self.get_multi(
            skip=skip, limit=limit, filters={"is_active": True}
        )

    async def get_users_by_role(self, role: str) -> list[User]:
        """Get all users with a specific role."""
        return await self.get_multi(filters={"role": role, "is_active": True})

    async def update_last_login(self, user_id: str) -> User | None:
        """Update the last_login_at timestamp."""
        return await self.update(
            user_id, last_login_at=datetime.now(timezone.utc)
        )

    async def activate_user(self, user_id: str) -> User | None:
        """Activate a user account."""
        return await self.update(user_id, is_active=True)

    async def deactivate_user(self, user_id: str) -> User | None:
        """Deactivate a user account."""
        return await self.update(user_id, is_active=False)