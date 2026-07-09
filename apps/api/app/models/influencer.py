"""Influencer models."""

import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, BigInteger, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class Influencer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "influencers"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str] = mapped_column(String(2), default="VE", nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    primary_tier: Mapped[str] = mapped_column(String(20), default="NANO", nullable=False)
    primary_handle: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    content_niches: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), default=lambda: ["es"], nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    source: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InfluencerSocialAccount(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "influencer_social_accounts"

    influencer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    handle: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    platform_user_id: Mapped[str | None] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class InfluencerMetricsSnapshot(Base, UUIDMixin):
    __tablename__ = "influencer_metrics_snapshot"

    influencer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False
    )
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("influencer_social_accounts.id", ondelete="CASCADE")
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    followers: Mapped[int | None] = mapped_column(BigInteger)
    following: Mapped[int | None] = mapped_column(BigInteger)
    posts_count: Mapped[int | None] = mapped_column(Integer)
    avg_likes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    avg_comments: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    avg_views: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    engagement_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    reach_30d: Mapped[int | None] = mapped_column(BigInteger)
    impressions_30d: Mapped[int | None] = mapped_column(BigInteger)
    audience_credibility: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    audience_quality: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    source: Mapped[str] = mapped_column(String(20), default="MANUAL", nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )