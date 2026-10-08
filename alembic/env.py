from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv

from app.database import Base, engine

# Import all SQLAlchemy models so Alembic can detect every table.
from app import models
from app import recipe_models
from app import pantry_models
from app import shopping_models
from app import meal_plan_models
from app import saved_recipe_models

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without opening a live database connection."""
    url = str(engine.url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using the application's SQLAlchemy engine."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
