"""necessary fields updated to text 2

Revision ID: fd374f205fd9
Revises: c636561bc58a
Create Date: 2026-01-16 09:16:05.270986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd374f205fd9'
down_revision: Union[str, None] = 'c636561bc58a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # user_links.link_type: VARCHAR(100) -> TEXT
    op.alter_column(
        "user_links",
        "link_type",
        type_=sa.Text(),
        existing_type=sa.String(length=100),
        nullable=True,
    )

    # posts_metadata.shortcode: VARCHAR(32) -> TEXT (PK)
    op.alter_column(
        "posts_metadata",
        "shortcode",
        type_=sa.Text(),
        existing_type=sa.String(length=32),
        nullable=False,
    )

    # posts_metadata.content_kind: VARCHAR(16) -> TEXT
    op.alter_column(
        "posts_metadata",
        "content_kind",
        type_=sa.Text(),
        existing_type=sa.String(length=16),
        nullable=False,
    )

    # post_media.post_shortcode: VARCHAR(32) -> TEXT (FK must match parent)
    op.alter_column(
        "post_media",
        "post_shortcode",
        type_=sa.Text(),
        existing_type=sa.String(length=32),
        nullable=False,
    )

    # post_media.media_type: VARCHAR(16) -> TEXT
    op.alter_column(
        "post_media",
        "media_type",
        type_=sa.Text(),
        existing_type=sa.String(length=16),
        nullable=False,
    )


def downgrade():
    # No downgrade: shrinking externally sourced text causes data loss.
    pass
