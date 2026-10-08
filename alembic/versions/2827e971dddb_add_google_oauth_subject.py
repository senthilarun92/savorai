"""add google oauth subject

Revision ID: 2827e971dddb
Revises: 3d1063cb2a92
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2827e971dddb"
down_revision: Union[str, Sequence[str], None] = "3d1063cb2a92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Google OAuth subject identifier."""

    op.add_column(
        "users",
        sa.Column(
            "google_sub",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_users_google_sub",
        "users",
        ["google_sub"],
        unique=True,
    )


def downgrade() -> None:
    """Remove Google OAuth subject identifier."""

    op.drop_index(
        "ix_users_google_sub",
        table_name="users",
    )

    op.drop_column(
        "users",
        "google_sub",
    )