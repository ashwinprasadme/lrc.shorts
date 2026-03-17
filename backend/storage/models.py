"""
SQLAlchemy ORM models.

Schema design:
- Story     : one row per story cluster (unique by RSS guid)
- Article   : one row per individual article within a cluster
              (unique by URL to prevent duplicates across fetches)

A Story has many Articles (1-to-many, cascade delete).
The lead article (is_lead=True) is the one that appears in the RSS <title>.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # RSS guid — stable identifier for the story cluster, used for dedup
    guid: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    # Clean headline (source suffix stripped)
    headline: Mapped[str] = mapped_column(Text, nullable=False)

    # URL-safe slug derived from the headline (e.g. "budget-2026-tax-cuts")
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    # Name of the primary/lead source (e.g. "The Hindu")
    primary_source: Mapped[str] = mapped_column(String, nullable=True)

    # When Google reports the story was published
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # When we first fetched/stored this story
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Original source URL of the featured image (from RSS feed media or og:image)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Filename of the locally stored JPEG (relative to IMAGES_DIR)
    # e.g. "my-story-slug.jpg"
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationship to clustered articles
    articles: Mapped[list["Article"]] = relationship(
        "Article",
        back_populates="story",
        cascade="all, delete-orphan",
        order_by="Article.position",
    )

    def __repr__(self) -> str:
        return f"<Story id={self.id} slug={self.slug!r}>"


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    story_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Article headline as it appears in the cluster list
    title: Mapped[str] = mapped_column(Text, nullable=False)

    # Direct (Google redirect) URL — unique to prevent duplicate rows
    url: Mapped[str] = mapped_column(Text, nullable=False)

    # Publisher name extracted from the description HTML
    source_name: Mapped[str] = mapped_column(String, nullable=True)

    # 0 = lead article, 1+ = secondary coverage (preserves display order)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # True only for the primary article of the cluster
    is_lead: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Final URL after all redirects (e.g. after Google News decodes the link)
    resolved_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Filename of the locally stored JPEG for this article (relative to IMAGES_DIR)
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Full article body text extracted via newspaper4k
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    story: Mapped["Story"] = relationship("Story", back_populates="articles")

    __table_args__ = (
        # Prevent same URL being stored twice for the same story
        UniqueConstraint("story_id", "url", name="uq_article_story_url"),
    )

    def __repr__(self) -> str:
        return f"<Article id={self.id} source={self.source_name!r} lead={self.is_lead}>"
