"""empty message

Revision ID: 0b21bd300cf2
Revises: 7993bc80adfc
Create Date: 2020-12-07 20:34:30.032671

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b21bd300cf2'
down_revision = '7993bc80adfc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('projects', sa.Column('enforce_assignment', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('projects', 'enforce_assignment')
    # ### end Alembic commands ###
