"""statement periods: the month an upload and its transactions count toward

Revision ID: c4d2a8e61f37
Revises: 9f8b4aa4478d
Create Date: 2026-11-01 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d2a8e61f37'
down_revision: Union[str, None] = '9f8b4aa4478d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

imports = sa.table('imports', sa.column('id', sa.Integer), sa.column('period_end', sa.Date), sa.column('period', sa.Date))
transactions = sa.table(
    'transactions',
    sa.column('id', sa.Integer),
    sa.column('import_id', sa.Integer),
    sa.column('booked_on', sa.Date),
    sa.column('period', sa.Date),
)


def upgrade() -> None:
    with op.batch_alter_table('imports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('period', sa.Date(), nullable=True))
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('period', sa.Date(), nullable=True))

    # Backfilled in Python so it runs the same on SQLite and Postgres: an upload counts
    # toward the month it ends in, a transaction added by hand toward its own month.
    conn = op.get_bind()
    periods = {}
    for import_id, period_end in conn.execute(sa.select(imports.c.id, imports.c.period_end)):
        if period_end is not None:
            periods[import_id] = period_end.replace(day=1)
            conn.execute(imports.update().where(imports.c.id == import_id).values(period=periods[import_id]))
    for tid, import_id, booked_on in conn.execute(
        sa.select(transactions.c.id, transactions.c.import_id, transactions.c.booked_on)
    ).all():
        period = periods.get(import_id) or booked_on.replace(day=1)
        conn.execute(transactions.update().where(transactions.c.id == tid).values(period=period))

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.alter_column('period', existing_type=sa.Date(), nullable=False)
        batch_op.create_index(batch_op.f('ix_transactions_period'), ['period'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_transactions_period'))
        batch_op.drop_column('period')
    with op.batch_alter_table('imports', schema=None) as batch_op:
        batch_op.drop_column('period')
