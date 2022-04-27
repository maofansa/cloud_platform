"""Domain adn Cdrom table

Revision ID: 59ab4dee883f
Revises: 2bf24b13fc05
Create Date: 2022-03-19 05:20:51.629302

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '59ab4dee883f'
down_revision = '2bf24b13fc05'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cdroms', schema=None) as batch_op:
        batch_op.add_column(sa.Column('url', sa.String(length=120), nullable=True))
        batch_op.drop_index('ix_cdroms_position')
        batch_op.create_index(batch_op.f('ix_cdroms_url'), ['url'], unique=True)
        batch_op.drop_column('position')

    with op.batch_alter_table('domains', schema=None) as batch_op:
        batch_op.drop_index('ix_domains_state')
        batch_op.drop_column('state')
        batch_op.drop_column('memory')
        batch_op.drop_column('cpu')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('domains', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cpu', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('memory', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('state', sa.VARCHAR(length=20), nullable=True))
        batch_op.create_index('ix_domains_state', ['state'], unique=False)

    with op.batch_alter_table('cdroms', schema=None) as batch_op:
        batch_op.add_column(sa.Column('position', sa.VARCHAR(length=120), nullable=True))
        batch_op.drop_index(batch_op.f('ix_cdroms_url'))
        batch_op.create_index('ix_cdroms_position', ['position'], unique=False)
        batch_op.drop_column('url')

    # ### end Alembic commands ###
