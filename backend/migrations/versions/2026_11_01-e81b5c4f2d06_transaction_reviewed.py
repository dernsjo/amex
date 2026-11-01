"""transaction reviewed: someone has gone through it and said whose it is

Revision ID: e81b5c4f2d06
Revises: d7a3f9b20c51
Create Date: 2026-11-01 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e81b5c4f2d06'
down_revision: Union[str, None] = 'd7a3f9b20c51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Everything imported so far starts unchecked; transactions added by hand were chosen by someone.
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reviewed', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute(sa.text('UPDATE transactions SET reviewed = :yes WHERE import_id IS NULL').bindparams(yes=True))


def downgrade() -> None:
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_column('reviewed')
