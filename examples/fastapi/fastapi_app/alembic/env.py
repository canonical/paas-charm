# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import sys

from alembic import context

sys.path.append(os.getcwd())

from app import Base, engine

config = context.config
target_metadata = Base.metadata


def run_migrations():
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
