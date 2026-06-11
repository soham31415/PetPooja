"""add restaurant tables and link sessions to tables

Revision ID: 3109328ec651
Revises: 16bdef8b60d1
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3109328ec651'
down_revision: Union[str, Sequence[str], None] = '16bdef8b60d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'restaurant_tables',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('qr_token', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('qr_token'),
    )
    op.create_index(op.f('ix_restaurant_tables_id'), 'restaurant_tables', ['id'], unique=False)
    op.create_index(op.f('ix_restaurant_tables_qr_token'), 'restaurant_tables', ['qr_token'], unique=True)

    op.add_column('dining_sessions', sa.Column('table_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_dining_sessions_table_id_restaurant_tables',
        'dining_sessions', 'restaurant_tables', ['table_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_dining_sessions_table_id_restaurant_tables', 'dining_sessions', type_='foreignkey')
    op.drop_column('dining_sessions', 'table_id')

    op.drop_index(op.f('ix_restaurant_tables_qr_token'), table_name='restaurant_tables')
    op.drop_index(op.f('ix_restaurant_tables_id'), table_name='restaurant_tables')
    op.drop_table('restaurant_tables')
