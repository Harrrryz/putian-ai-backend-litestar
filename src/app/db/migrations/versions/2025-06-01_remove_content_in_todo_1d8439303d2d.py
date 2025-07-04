# type: ignore
"""remove content in todo

Revision ID: 1d8439303d2d
Revises: 41db89243be7
Create Date: 2025-06-01 03:40:21.106912+00:00

"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from advanced_alchemy.types import EncryptedString, EncryptedText, GUID, ORA_JSONB, DateTimeUTC
from sqlalchemy import Text  # noqa: F401

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade", "schema_upgrades", "schema_downgrades", "data_upgrades", "data_downgrades"]

sa.GUID = GUID
sa.DateTimeUTC = DateTimeUTC
sa.ORA_JSONB = ORA_JSONB
sa.EncryptedString = EncryptedString
sa.EncryptedText = EncryptedText

# revision identifiers, used by Alembic.
revision = '1d8439303d2d'
down_revision = '41db89243be7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_upgrades()
            data_upgrades()

def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_downgrades()
            schema_downgrades()

def schema_upgrades() -> None:
    """schema upgrade migrations go here."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('tag', schema=None) as batch_op:
        batch_op.create_table_comment(
        'Tags for todos',
        existing_comment=None
    )

    with op.batch_alter_table('todo', schema=None) as batch_op:
        batch_op.drop_index('ix_todo_content')
        batch_op.create_table_comment(
        'Todo items',
        existing_comment=None
    )
        batch_op.drop_column('content')

    with op.batch_alter_table('user_account_todo_tag', schema=None) as batch_op:
        batch_op.create_table_comment(
        'Links a user to a specific todo tag.',
        existing_comment=None
    )

    # ### end Alembic commands ###

def schema_downgrades() -> None:
    """schema downgrade migrations go here."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_account_todo_tag', schema=None) as batch_op:
        batch_op.drop_table_comment(
        existing_comment='Links a user to a specific todo tag.'
    )

    with op.batch_alter_table('todo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('content', sa.VARCHAR(length=320), autoincrement=False, nullable=False))
        batch_op.drop_table_comment(
        existing_comment='Todo items'
    )
        batch_op.create_index('ix_todo_content', ['content'], unique=False)

    with op.batch_alter_table('tag', schema=None) as batch_op:
        batch_op.drop_table_comment(
        existing_comment='Tags for todos'
    )

    # ### end Alembic commands ###

def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""

def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
