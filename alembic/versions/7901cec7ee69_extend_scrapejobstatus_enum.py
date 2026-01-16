"""extend scrapejobstatus enum

Revision ID: 7901cec7ee69
Revises: 45a97657f53e
Create Date: 2026-01-16 07:31:43.211920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7901cec7ee69'
down_revision: Union[str, None] = '45a97657f53e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'USER_SEED_RUNNING'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'USER_SEEDED'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'USER_SEEDED_FAILED'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'POSTS_SEED_RUNNING'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'POSTS_SEEDED'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'POSTS_SEEDED_FAILED'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'SCRAPE_DONE'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'RATE_LIMITED'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'FAILED'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'DEAD'")
    

def downgrade() -> None:
    """Downgrade schema."""
    pass
