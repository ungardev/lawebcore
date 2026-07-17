"""Pydantic schemas for the Discovery module."""

from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DiscoveryRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CandidateStatus(str, Enum):
    NEW = "new"
    SAVED = "saved"
    DISMISSED = "dismissed"
    CONTACTED = "contacted"
    REPLIED = "replied"
    WON = "won"
    LOST = "lost"


class ConversationStep(str, Enum):
    START = "start"
    BRIEF = "brief"
    REFINING = "refining"
    SEARCHING = "searching"
    RANKING = "ranking"
    CANDIDATES_REVIEW = "candidates_review"
    DONE = "done"


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    X = "x"
    FACEBOOK = "facebook"


class AudienceGender(str, Enum):
    FEMALE = "female"
    MALE = "male"
    ALL = "all"


class BriefStructured(BaseModel):
    product_name: str | None = None
    brand_id: UUID | None = None
    industry: str | None = None
    niches: list[str] = Field(default_factory=list)
    audience_gender: AudienceGender = AudienceGender.ALL
    audience_age_min: int = 18
    audience_age_max: int = 65
    audience_countries: list[str] = Field(default_factory=list)
    audience_cities: list[str] = Field(default_factory=list)
    budget_usd: float | None = None
    tone: list[str] = Field(default_factory=list)
    platforms: list[Platform] = Field(default_factory=list)
    additional_context: str = ""


class CandidateMetrics(BaseModel):
    platform: Platform
    platform_user_id: str | None = None
    handle: str
    url: str | None = None
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None

    country: str | None = None
    city: str | None = None
    language_primary: str = "es"

    followers: int | None = None
    following: int | None = None
    posts_count: int | None = None
    avg_likes: int | None = None
    avg_comments: int | None = None
    avg_views: int | None = None
    engagement_rate: float | None = None

    audience_credibility: float | None = None
    audience_quality: float | None = None
    audience_gender_split: dict[str, float] | None = None
    audience_age_buckets: dict[str, float] | None = None
    audience_top_countries: list[dict[str, Any]] | None = None
    audience_top_cities: list[dict[str, Any]] | None = None
    audience_interests: list[str] = Field(default_factory=list)

    source_actor_run_id: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class MatchScoreResult(BaseModel):
    match_score: float = Field(ge=0, le=100)
    niche_relevance: float = Field(ge=0, le=100)
    geo_relevance: float = Field(ge=0, le=100)
    audience_relevance: float = Field(ge=0, le=100)
    content_quality: float = Field(ge=0, le=100)
    estimated_cost: float | None = None
    expected_reach: int | None = None
    expected_engagement: float | None = None
    roi_estimate: float | None = None
    rationale: str = ""


class CandidateWithScore(BaseModel):
    id: UUID
    metrics: CandidateMetrics
    score: MatchScoreResult
    status: CandidateStatus = CandidateStatus.NEW


class DiscoveryConversationCreate(BaseModel):
    bu_id: UUID | None = None
    initial_brief: str | None = None


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    reasoning: str | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: str


class ConversationResponse(BaseModel):
    id: UUID
    current_step: ConversationStep | None = None
    discovery_run_id: UUID | None = None
    accumulated_brief: str | None = None
    message_count: int = 0
    status: str = "active"
    started_at: str
    last_message_at: str


class DiscoverySearchRequest(BaseModel):
    product_name: str | None = None
    brand_id: UUID | None = None
    industry: str | None = None
    niches: list[str] = Field(default_factory=list)
    audience_gender: AudienceGender = AudienceGender.ALL
    audience_age_min: int = 18
    audience_age_max: int = 65
    audience_countries: list[str] = Field(default_factory=["VE"])
    audience_cities: list[str] = Field(default_factory=list)
    budget_usd: float | None = None
    tone: list[str] = Field(default_factory=list)
    platforms: list[Platform] = Field(default_factory=[Platform.INSTAGRAM])
    max_candidates: int = Field(default=20, ge=1, le=100)


class DiscoveryRunResponse(BaseModel):
    id: UUID
    status: DiscoveryRunStatus
    total_candidates: int = 0
    accepted: int = 0
    actual_cost_usd: float | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str
    metadata: dict = {}


class ApiCostRecord(BaseModel):
    provider: str
    operation: str | None = None
    cost_usd: float
    request_count: int = 1
    tokens_input: int | None = None
    tokens_output: int | None = None
    occurred_at: str | None = None
