"""Alembic migration script template."""

revision: str = "{{revision}}"
down_revision: str | None = "{{down_revision}}"
branch_labels: str | None = "{{branch_labels}}"
depends_on: str | None = "{{depends_on}}"


from typing import Sequence

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Upgrade to this revision."""
    pass


def downgrade() -> None:
    """Downgrade from this revision."""
    pass