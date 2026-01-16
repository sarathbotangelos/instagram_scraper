from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Text,
    CheckConstraint,
    UniqueConstraint,
    ForeignKey,
    DateTime
)
from datetime import datetime, UTC

from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.app.core.db.base import Base
from sqlalchemy import func
import enum
from sqlalchemy import Enum as SAEnum




class ScrapeJobType(enum.Enum):
    PROFILE = 1
    POST = 2

class ScrapeJobSource(enum.Enum):
    GOOGLE = 1
    FOLLOWUP = 2
    MANUAL = 3


class ScrapeJobStatus(enum.Enum):
    PENDING = 1
    USER_CREATED = 2
    USER_CREATION_FAILED = 3
    USER_CREATION_RUNNING = 4
    USER_SEED_RUNNING = 5
    USER_SEEDED = 6
    USER_SEEDED_FAILED = 7
    POSTS_SEED_RUNNING = 8
    POSTS_SEEDED = 9
    POSTS_SEEDED_FAILED = 10
    SCRAPE_DONE = 11
    RATE_LIMITED = 12
    FAILED = 13
    DEAD = 14


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    job_type: Mapped[ScrapeJobType] = mapped_column(
        SAEnum(ScrapeJobType, name="scrapejobtype"),
        nullable=False,
    )

    entity_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source: Mapped[ScrapeJobSource] = mapped_column(
        SAEnum(ScrapeJobSource, name="scrapejobsource"),
        nullable=False,
    )

    status: Mapped[ScrapeJobStatus] = mapped_column(
        SAEnum(ScrapeJobStatus, name="scrapejobstatus"),
        nullable=False,
        default=ScrapeJobStatus.PENDING,
        server_default="PENDING",
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    retry_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "job_type",
            "entity_key",
            name="uq_scrape_jobs_job_type_entity_key",
        ),
    )



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    username: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    bio_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    profile_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    followers_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    following_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    posts_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # created at with auto population
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # updated at with auto population
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "length(username) > 0",
            name="ck_users_username_not_empty",
        ),
    )


class UserLink(Base):
    __tablename__ = "user_links"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    link_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,   # website | pinterest | whatsapp | email | other
    )

    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "url",
            name="uq_user_links_user_url",
        ),
        CheckConstraint(
            "length(url) > 0",
            name="ck_user_links_url_not_empty",
        ),
    )


class PostsMetadata(Base):
    __tablename__ = "posts_metadata"

    shortcode: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
    )

    posted_by: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    posted_on: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    caption: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    likes_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    comments_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    views_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    content_kind: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    is_container: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    collaborators: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",   # JSON array of usernames
    )

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    media_items: Mapped[list["PostMedia"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "content_kind IN ('post','reel')",
            name="ck_posts_content_kind",
        ),
        CheckConstraint(
            "(content_kind = 'reel' AND is_container = FALSE) OR (content_kind = 'post')",
            name="ck_posts_container_validity",
        ),
    )


class PostMedia(Base):
    __tablename__ = "post_media"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    post_shortcode: Mapped[str] = mapped_column(
        String(32),
        ForeignKey(
            "posts_metadata.shortcode",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    media_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    media_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    media_subtype: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    media_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    tagged_users: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",   # JSON array of usernames
    )

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    post: Mapped["PostsMetadata"] = relationship(
        back_populates="media_items",
    )

    __table_args__ = (
        CheckConstraint(
            "media_type IN ('image','video')",
            name="ck_media_type",
        ),
        UniqueConstraint(
            "post_shortcode",
            "media_index",
            name="uq_post_media_index",
        ),
    )


