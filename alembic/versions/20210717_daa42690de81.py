"""
Хэширование сессионого идентификатора

Revision ID: daa42690de81
Revises: 71bcf0a63639
Create Date: 2021-07-17 09:08:19.502376

"""
from alembic import op
import sqlalchemy as sa
import cyberdas.utils.hash_type


# revision identifiers, used by Alembic.
revision = 'daa42690de81'
down_revision = '71bcf0a63639'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('sessions', 'sid', type_=cyberdas.utils.hash_type.HashType('sha256'),
                    postgresql_using='sid::bytea')
    op.alter_column('sessions', 'csrf_token', type_=sa.String(64),
                    postgresql_using='csrf_token::varchar(64)')
    op.alter_column('sessions', 'ip', type_=sa.String(16),
                    postgresql_using='ip::varchar(16)')


def downgrade():
    op.alter_column('sessions', 'sid', type_=sa.String(),
                    postgresql_using='sid::varchar')
    op.alter_column('sessions', 'csrf_token', type_=sa.String(),
                    postgresql_using='csrf_token::varchar')
    op.alter_column('sessions', 'ip', type_=sa.String(),
                    postgresql_using='ip::varchar')
