from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from flask import current_app
from sqlalchemy import engine_from_config, pool


config = context.config
fileConfig(config.config_file_name)


def get_url():
    return current_app.config.get("SQLALCHEMY_DATABASE_URI")


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=current_app.extensions["migrate"].db.metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=current_app.extensions["migrate"].db.metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

