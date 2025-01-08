# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Initial migration

Revision ID: eca6177bd16a
Revises: 
Create Date: 2023-09-05 17:12:56.303534

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eca6177bd16a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(80), unique=True, nullable=False),
        sa.Column("password", sa.String(256), nullable=False),
    )


def downgrade():
    op.drop_table("users")
