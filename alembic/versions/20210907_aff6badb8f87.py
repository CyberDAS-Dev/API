"""
Убраны часовые пояса

Revision ID: aff6badb8f87
Revises: 22d32aac74f7
Create Date: 2021-09-07 01:05:37.881411

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aff6badb8f87'
down_revision = '22d32aac74f7'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('sessions', 'expires', type_=sa.DateTime(timezone = False), postgresql_using='expires::timestamp')
    op.alter_column('sessions', 'created_at', type_=sa.DateTime(timezone = False), postgresql_using='created_at::timestamp')
    op.alter_column('users', 'created_at', type_=sa.DateTime(timezone = False), postgresql_using='created_at::timestamp')
    op.alter_column('users', 'last_session', type_=sa.DateTime(timezone = False), postgresql_using='last_session::timestamp')


def downgrade():
    op.alter_column('sessions', 'expires', type_=sa.DateTime(timezone = True), postgresql_using='expires::timestamptz')
    op.alter_column('sessions', 'created_at', type_=sa.DateTime(timezone = True), postgresql_using='created_at::timestamptz')
    op.alter_column('users', 'created_at', type_=sa.DateTime(timezone = True), postgresql_using='created_at::timestamptz')
    op.alter_column('users', 'last_session', type_=sa.DateTime(timezone = True), postgresql_using='last_session::timestamptz')
