"""
Переделка сессий

Revision ID: 37a06deaec23
Revises: 207c14670fcd
Create Date: 2021-08-15 17:24:45.331833

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '37a06deaec23'
down_revision = '207c14670fcd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('long_sessions')
    op.drop_column('sessions', 'unsafe')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'password')
    op.drop_column('users', 'last_seen')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('last_seen', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('users', sa.Column('password', postgresql.BYTEA(), autoincrement=False, nullable=False))
    op.add_column('users', sa.Column('email_verified', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.add_column('sessions', sa.Column('unsafe', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.create_table('long_sessions',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('selector', sa.VARCHAR(length=16), autoincrement=False, nullable=False),
    sa.Column('validator', postgresql.BYTEA(), autoincrement=False, nullable=False),
    sa.Column('associated_sid', postgresql.BYTEA(), autoincrement=False, nullable=True),
    sa.Column('uid', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('user_agent', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('ip', sa.VARCHAR(length=16), autoincrement=False, nullable=False),
    sa.Column('expires', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['associated_sid'], ['sessions.sid'], name='fk_long_sessions_associated_sid_sessions'),
    sa.ForeignKeyConstraint(['uid'], ['users.id'], name='fk_long_sessions_uid_users'),
    sa.PrimaryKeyConstraint('id', name='pk_long_sessions'),
    sa.UniqueConstraint('selector', name='uq_long_sessions_selector')
    )
    # ### end Alembic commands ###
