"""add auth fields and recipe ownership

Revision ID: 3d1063cb2a92
Revises: 5cb42ca804ce
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3d1063cb2a92"
down_revision: Union[str, Sequence[str], None] = "5cb42ca804ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Safely add authentication fields and recipe ownership."""

    # Add auth fields as nullable first so existing rows remain valid.
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=30), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("true"),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Backfill the existing legacy user's username.
    # This migration is specifically for the current V2 database,
    # which currently has one legacy user (id=1).
    op.execute(
        sa.text(
            """
            UPDATE users
            SET username =
                left(
                    regexp_replace(
                        lower(
                            coalesce(
                                nullif(trim(name), ''),
                                split_part(email, '@', 1)
                            )
                        ),
                        '[^a-z0-9_]+',
                        '_',
                        'g'
                    ),
                    24
                ) || '_' || id::text
            WHERE username IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            "UPDATE users SET is_active = true "
            "WHERE is_active IS NULL"
        )
    )

    op.execute(
        sa.text(
            "UPDATE users SET email_verified = false "
            "WHERE email_verified IS NULL"
        )
    )

    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(length=30),
        nullable=False,
    )

    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
    )

    op.alter_column(
        "users",
        "email_verified",
        existing_type=sa.Boolean(),
        nullable=False,
    )

    op.alter_column(
        "users",
        "email",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )

    op.create_index(
        "ix_users_username",
        "users",
        ["username"],
        unique=True,
    )

    # Add recipe ownership as nullable during transition.
    op.add_column(
        "recipes",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )

    # Backfill all existing recipes to the first/legacy user.
    # Using a SQL subquery keeps the migration compatible with
    # both online execution and `alembic upgrade --sql`.
    op.execute(
        sa.text(
            """
            UPDATE recipes
            SET user_id = (
                SELECT id
                FROM users
                ORDER BY id
                LIMIT 1
            )
            WHERE user_id IS NULL
            """
        )
    )

    # If no user existed, this NOT NULL transition fails safely
    # inside the transaction rather than creating orphaned recipes.
    op.alter_column(
        "recipes",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_index(
        "ix_recipes_user_id",
        "recipes",
        ["user_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_recipes_user_id_users",
        "recipes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Reverse authentication and recipe ownership changes."""

    op.drop_constraint(
        "fk_recipes_user_id_users",
        "recipes",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_recipes_user_id",
        table_name="recipes",
    )

    op.drop_column("recipes", "user_id")

    op.drop_index(
        "ix_users_username",
        table_name="users",
    )

    op.alter_column(
        "users",
        "email",
        existing_type=sa.VARCHAR(length=255),
        nullable=True,
    )

    op.drop_column("users", "last_login_at")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "is_active")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
