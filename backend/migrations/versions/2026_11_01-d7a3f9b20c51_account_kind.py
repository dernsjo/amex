"""account kind: debit (paid as spent) or credit (paid later, as a bill)

Revision ID: d7a3f9b20c51
Revises: c4d2a8e61f37
Create Date: 2026-11-01 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a3f9b20c51'
down_revision: Union[str, None] = 'c4d2a8e61f37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

accounts = sa.table('accounts', sa.column('id', sa.Integer), sa.column('import_config', sa.JSON), sa.column('kind', sa.String))


def upgrade() -> None:
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('kind', sa.Enum('debit', 'credit', name='accountkind', native_enum=False, length=20),
                      server_default='debit', nullable=False)
        )
    # Accounts that read Amex exports are credit cards; everything else stays a bank account.
    conn = op.get_bind()
    for account_id, config in conn.execute(sa.select(accounts.c.id, accounts.c.import_config)).all():
        if config and config.get('importer') == 'amex_se':
            conn.execute(accounts.update().where(accounts.c.id == account_id).values(kind='credit'))


def downgrade() -> None:
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_column('kind')
