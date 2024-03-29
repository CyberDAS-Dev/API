"""
Новое поле - only_one_active в очередях

Revision ID: a9144fad477a
Revises: 697876a4d7da
Create Date: 2021-08-31 07:09:31.334952

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = 'a9144fad477a'
down_revision = '697876a4d7da'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('queues', sa.Column('only_one_active', sa.Boolean(), server_default='false', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('queues', 'only_one_active')
    # ### end Alembic commands ###
