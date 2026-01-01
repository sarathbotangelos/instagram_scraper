"""update_models_to_datetime

Revision ID: 18176a12e9fd
Revises: d1a657c2021a
Create Date: 2026-01-01 14:20:05.863044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18176a12e9fd'
down_revision: Union[str, None] = 'd1a657c2021a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # post_media.scraped_at (INTEGER epoch → timestamptz)
    op.execute("""
        ALTER TABLE post_media
        ALTER COLUMN scraped_at
        TYPE TIMESTAMPTZ
        USING to_timestamp(scraped_at)
    """)

    # posts_metadata.posted_on (nullable)
    op.execute("""
        ALTER TABLE posts_metadata
        ALTER COLUMN posted_on
        TYPE TIMESTAMPTZ
        USING to_timestamp(posted_on)
    """)

    # posts_metadata.scraped_at
    op.execute("""
        ALTER TABLE posts_metadata
        ALTER COLUMN scraped_at
        TYPE TIMESTAMPTZ
        USING to_timestamp(scraped_at)
    """)

    # user_links.extracted_at
    op.execute("""
        ALTER TABLE user_links
        ALTER COLUMN extracted_at
        TYPE TIMESTAMPTZ
        USING to_timestamp(extracted_at)
    """)

    # users.scraped_at
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN scraped_at
        TYPE TIMESTAMPTZ
        USING to_timestamp(scraped_at)
    """)

    # OPTIONAL but recommended: add server defaults where appropriate
    op.alter_column(
        "users",
        "scraped_at",
        server_default=sa.func.now(),
        nullable=False,
    )


def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN scraped_at
        TYPE INTEGER
        USING EXTRACT(EPOCH FROM scraped_at)::INTEGER
    """)

    op.execute("""
        ALTER TABLE user_links
        ALTER COLUMN extracted_at
        TYPE INTEGER
        USING EXTRACT(EPOCH FROM extracted_at)::INTEGER
    """)

    op.execute("""
        ALTER TABLE posts_metadata
        ALTER COLUMN scraped_at
        TYPE INTEGER
        USING EXTRACT(EPOCH FROM scraped_at)::INTEGER
    """)

    op.execute("""
        ALTER TABLE posts_metadata
        ALTER COLUMN posted_on
        TYPE INTEGER
        USING EXTRACT(EPOCH FROM posted_on)::INTEGER
    """)

    op.execute("""
        ALTER TABLE post_media
        ALTER COLUMN scraped_at
        TYPE INTEGER
        USING EXTRACT(EPOCH FROM scraped_at)::INTEGER
    """)
