"""
Система обратной связи

Revision ID: 8f917ab94755
Revises: aff6badb8f87
Create Date: 2021-09-18 08:45:50.489909

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = '8f917ab94755'
down_revision = 'aff6badb8f87'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('recipients',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('email', sqlalchemy_utils.types.email.EmailType(length=255), nullable=True),
    sa.PrimaryKeyConstraint('name', name=op.f('pk_recipients'))
    )
    op.create_table('feedback_categories',
    sa.Column('recipient_name', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['recipient_name'], ['recipients.name'], name=op.f('fk_feedback_categories_recipient_name_recipients')),
    sa.PrimaryKeyConstraint('recipient_name', 'name', name=op.f('pk_feedback_categories'))
    )
    op.create_table('feedbacks',
    sa.Column('recipient_name', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('email', sqlalchemy_utils.types.email.EmailType(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['recipient_name', 'category'], ['feedback_categories.recipient_name', 'feedback_categories.name'], name=op.f('fk_feedbacks_recipient_name_feedback_categories')),
    sa.ForeignKeyConstraint(['recipient_name'], ['recipients.name'], name=op.f('fk_feedbacks_recipient_name_recipients')),
    sa.PrimaryKeyConstraint('recipient_name', 'id', name=op.f('pk_feedbacks'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('feedbacks')
    op.drop_table('feedback_categories')
    op.drop_table('recipients')
    # ### end Alembic commands ###