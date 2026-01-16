"""extend scrape jobs for better tracing

Revision ID: a1eb417c774c
Revises: 7901cec7ee69
Create Date: 2026-01-16 07:43:38.079075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1eb417c774c'
down_revision: Union[str, None] = '7901cec7ee69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'USER_CREATED'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'USER_CREATION_FAILED'")
    op.execute("ALTER TYPE scrapejobstatus ADD VALUE IF NOT EXISTS 'USER_CREATION_RUNNING'")

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


def downgrade():
    # PostgreSQL enums cannot safely drop values.
    pass