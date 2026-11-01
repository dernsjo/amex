"""drop legacy tables

The PoC data was not worth importing, so the tables kept by the multi-tenant
migration go. Downgrading recreates them empty.

Revision ID: 7c1d2e9a4b30
Revises: 4ef6e97fe4ce
Create Date: 2026-11-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1d2e9a4b30'
down_revision: Union[str, None] = '4ef6e97fe4ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dropping a table drops its indexes too.
    op.drop_table('legacy_expenses')
    op.drop_table('legacy_users')


def downgrade() -> None:
    # Same shape as the initial schema; the previous revision renames them back.
    op.create_table('legacy_expenses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('paid_by', sa.String(length=100), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id', name='legacy_expenses_pkey')
    )
    op.create_index('ix_expenses_date', 'legacy_expenses', ['date'], unique=False)
    op.create_table('legacy_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name='legacy_users_pkey')
    )
    op.create_index('ix_users_name', 'legacy_users', ['name'], unique=True)
