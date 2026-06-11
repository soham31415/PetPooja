"""add owner to restaurants

Revision ID: 16bdef8b60d1
Revises: 431df9fb5117
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16bdef8b60d1'
down_revision: Union[str, Sequence[str], None] = '431df9fb5117'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('restaurants', sa.Column('owner_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_restaurants_owner_id_users', 'restaurants', 'users', ['owner_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_restaurants_owner_id_users', 'restaurants', type_='foreignkey')
    op.drop_column('restaurants', 'owner_id')
