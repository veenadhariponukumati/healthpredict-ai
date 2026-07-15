"""Idempotent seed script — creates the default local-dev users documented in
LOCAL_SETUP.md if they don't already exist. Safe to run on every startup.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User
from app.db.session import async_session_factory

DEFAULT_USERS = [
    {"email": "admin@test.com", "full_name": "Admin User", "role": "admin"},
    {"email": "clinician@test.com", "full_name": "Clinician User", "role": "clinician"},
    {"email": "viewer@test.com", "full_name": "Viewer User", "role": "viewer"},
]
DEFAULT_PASSWORD = "Test123!"


async def seed_default_users() -> None:
    async with async_session_factory() as session:
        for entry in DEFAULT_USERS:
            existing = await session.execute(
                select(User).where(User.email == entry["email"])
            )
            if existing.scalar_one_or_none() is not None:
                continue
            session.add(
                User(
                    email=entry["email"],
                    password_hash=hash_password(DEFAULT_PASSWORD),
                    full_name=entry["full_name"],
                    role=entry["role"],
                    is_active=True,
                )
            )
            print(f"[seed] Created default user: {entry['email']} ({entry['role']})")
        await session.commit()


if __name__ == "__main__":
    print(f"[seed] Seeding default users against {settings.ENVIRONMENT} database...")
    asyncio.run(seed_default_users())
