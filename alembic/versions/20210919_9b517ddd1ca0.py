"""
Опциональность указания факультета пользователя

Revision ID: 9b517ddd1ca0
Revises: 8f917ab94755
Create Date: 2021-09-19 11:52:54.867078

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = '9b517ddd1ca0'
down_revision = '8f917ab94755'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('users', 'faculty_id', nullable = True)


def downgrade():
    op.alter_column('users', 'faculty_id', nullable = False)
