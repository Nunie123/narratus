"""empty message

Revision ID: eeba2c2abaac
Revises: 135d6febb1b0
Create Date: 2018-01-23 02:04:48.721095

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eeba2c2abaac'
down_revision = '135d6febb1b0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chart', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_chart_user_id'), 'chart', ['user_id'], unique=False)
    op.drop_index('ix_chart_creator', table_name='chart')
    op.drop_constraint(None, 'chart', type_='foreignkey')
    op.create_foreign_key(None, 'chart', 'user', ['user_id'], ['id'])
    op.drop_column('chart', 'creator')
    op.add_column('contact', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_contact_user_id'), 'contact', ['user_id'], unique=False)
    op.drop_index('ix_contact_creator', table_name='contact')
    op.drop_constraint(None, 'contact', type_='foreignkey')
    op.create_foreign_key(None, 'contact', 'user', ['user_id'], ['id'])
    op.drop_column('contact', 'creator')
    op.add_column('query', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_query_user_id'), 'query', ['user_id'], unique=False)
    op.drop_index('ix_query_creator', table_name='query')
    op.drop_constraint(None, 'query', type_='foreignkey')
    op.create_foreign_key(None, 'query', 'user', ['user_id'], ['id'])
    op.drop_column('query', 'creator')
    op.add_column('report', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_report_user_id'), 'report', ['user_id'], unique=False)
    op.drop_index('ix_report_creator', table_name='report')
    op.drop_constraint(None, 'report', type_='foreignkey')
    op.create_foreign_key(None, 'report', 'user', ['user_id'], ['id'])
    op.drop_column('report', 'creator')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('report', sa.Column('creator', sa.INTEGER(), nullable=True))
    op.drop_constraint(None, 'report', type_='foreignkey')
    op.create_foreign_key(None, 'report', 'user', ['creator'], ['id'])
    op.create_index('ix_report_creator', 'report', ['creator'], unique=False)
    op.drop_index(op.f('ix_report_user_id'), table_name='report')
    op.drop_column('report', 'user_id')
    op.add_column('query', sa.Column('creator', sa.INTEGER(), nullable=True))
    op.drop_constraint(None, 'query', type_='foreignkey')
    op.create_foreign_key(None, 'query', 'user', ['creator'], ['id'])
    op.create_index('ix_query_creator', 'query', ['creator'], unique=False)
    op.drop_index(op.f('ix_query_user_id'), table_name='query')
    op.drop_column('query', 'user_id')
    op.add_column('contact', sa.Column('creator', sa.INTEGER(), nullable=True))
    op.drop_constraint(None, 'contact', type_='foreignkey')
    op.create_foreign_key(None, 'contact', 'user', ['creator'], ['id'])
    op.create_index('ix_contact_creator', 'contact', ['creator'], unique=False)
    op.drop_index(op.f('ix_contact_user_id'), table_name='contact')
    op.drop_column('contact', 'user_id')
    op.add_column('chart', sa.Column('creator', sa.INTEGER(), nullable=True))
    op.drop_constraint(None, 'chart', type_='foreignkey')
    op.create_foreign_key(None, 'chart', 'user', ['creator'], ['id'])
    op.create_index('ix_chart_creator', 'chart', ['creator'], unique=False)
    op.drop_index(op.f('ix_chart_user_id'), table_name='chart')
    op.drop_column('chart', 'user_id')
    # ### end Alembic commands ###
