"""empty message

Revision ID: b3ea42253bcd
Revises: cb8a379b2317
Create Date: 2021-02-12 18:19:39.874568

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3ea42253bcd'
down_revision = 'cb8a379b2317'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('projects', sa.Column('prevent_adjacent_task_lock', sa.Boolean(), nullable=True))
    op.drop_column('projects', 'adjacent_task_lock')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('projects', sa.Column('adjacent_task_lock', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_column('projects', 'prevent_adjacent_task_lock')
    # ### end Alembic commands ###
