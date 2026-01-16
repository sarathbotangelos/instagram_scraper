"""necessary fields updated to text

Revision ID: c636561bc58a
Revises: 8be808a43264
Create Date: 2026-01-16 09:14:41.401206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c636561bc58a'
down_revision: Union[str, None] = '8be808a43264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
