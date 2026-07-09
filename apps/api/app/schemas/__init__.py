"""Pydantic schemas for API serialization."""

from datetime import datetime, date
from decimal import Decimal
from typing import Annotated, Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


T = TypeVar("T")


class ORMModel(BaseModel):
    """Base schema that reads from SQLAlchemy ORM models."""
    model_config = ConfigDict(from_attributes=True)


# ---------- Common ----------

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)
    search: str | None = None
    sort_by: str | None = None
    sort_dir: str = Field(default="desc", pattern="^(asc|desc)$")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------- Identity ----------

class BusinessUnitRead(ORMModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    is_active: bool


class UserRead(ORMModel):
    id: UUID
    email: str
    full_name: str
    avatar_url: str | None = None
    job_title: str | None = None
    primary_bu_id: UUID | None = None
    status: str
    last_login_at: datetime | None = None
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    job_title: str | None = None
    avatar_url: str | None = None
    phone: str | None = None


class RoleRead(ORMModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool
    is_active: bool


# ---------- Commercial ----------

class ClientRead(ORMModel):
    id: UUID
    code: str
    name: str
    legal_name: str | None = None
    industry: str | None = None
    website: str | None = None
    logo_url: str | None = None
    is_active: bool
    created_at: datetime


class ClientCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = None
    tax_id: str | None = None
    industry: str | None = None
    website: str | None = None


class BrandRead(ORMModel):
    id: UUID
    client_id: UUID
    code: str
    name: str
    category: str | None = None
    logo_url: str | None = None
    is_active: bool
    created_at: datetime


class BrandCreate(BaseModel):
    client_id: UUID
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None


# ---------- Influencers ----------

class InfluencerRead(ORMModel):
    id: UUID
    full_name: str
    email: str | None = None
    country: str
    primary_tier: str
    primary_handle: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    content_niches: list[str]
    languages: list[str]
    status: str
    tags: list[str]
    created_at: datetime


class InfluencerCreate(BaseModel):
    full_name: str
    email: EmailStr | None = None
    phone: str | None = None
    country: str = "VE"
    primary_tier: str = "NANO"
    primary_handle: str | None = None
    bio: str | None = None
    content_niches: list[str] = []
    languages: list[str] = ["es"]
    tags: list[str] = []
    source: str | None = None
    source_id: str | None = None


class InfluencerMetricsRead(ORMModel):
    id: UUID
    influencer_id: UUID
    snapshot_date: date
    followers: int | None = None
    engagement_rate: Decimal | None = None
    avg_views: Decimal | None = None
    reach_30d: int | None = None
    audience_credibility: Decimal | None = None
    source: str


# ---------- Campaigns ----------

class CampaignRead(ORMModel):
    id: UUID
    code: str
    client_id: UUID
    brand_id: UUID
    name: str
    objective: str
    influencer_tiers: list[str]
    start_date: date | None = None
    end_date: date | None = None
    budget_total: Decimal | None = None
    budget_currency: str
    num_influencers: int
    status: str
    owner_user_id: UUID | None = None
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    client_id: UUID
    brand_id: UUID
    name: str = Field(min_length=1, max_length=255)
    objective: str
    campaign_type: str | None = None
    secondary_objectives: list[str] = []
    influencer_tiers: list[str] = []
    start_date: date | None = None
    end_date: date | None = None
    budget_total: Decimal | None = None
    num_influencers: int = 0
    target_audience: str | None = None
    tags: list[str] = []
    notes: str | None = None

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, v):
        allowed = {"AWARENESS", "CONSIDERACION", "CONVERSION", "GESTION_DE_CRISIS", "BRANDING", "LANZAMIENTO", "RETENCION"}
        if v.upper() not in allowed:
            raise ValueError(f"objective must be one of {allowed}")
        return v.upper()


class CampaignUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget_total: Decimal | None = None
    status: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class CampaignStatusChange(BaseModel):
    to_status: str
    reason: str | None = None


class CampaignKPIRead(BaseModel):
    kpi_code: str
    kpi_name: str
    category: str
    value: Decimal
    source: str
    recorded_at: datetime


class CampaignDetail(CampaignRead):
    brand: BrandRead | None = None
    client: ClientRead | None = None
    kpis: list[CampaignKPIRead] = []
    links: list["CampaignLinkRead"] = []
    insights: list["InsightRead"] = []


class CampaignLinkRead(ORMModel):
    id: UUID
    campaign_id: UUID
    link_type: str
    title: str
    url: str
    description: str | None = None


# ---------- KPIs ----------

class KPIRead(ORMModel):
    code: str
    name: str
    description: str | None
    category: str
    unit: str
    higher_is_better: bool


class KPIValueCreate(BaseModel):
    campaign_id: UUID
    kpi_code: str
    value: Decimal
    period_start: date | None = None
    period_end: date | None = None
    source: str = "MANUAL"
    notes: str | None = None


class InsightRead(ORMModel):
    id: UUID
    campaign_id: UUID
    insight_type: str
    title: str
    description: str
    is_winning_format: bool
    generated_by_ai: bool
    created_at: datetime


# ---------- AI ----------

class AIChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str
    context_type: str | None = None  # 'campaign' | 'client' | 'brand' | 'global'
    context_id: UUID | None = None


class AIChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    sources: list[dict] = []
    tokens_used: int = 0
    latency_ms: int = 0


class AIGenerateRequest(BaseModel):
    prompt_code: str  # 'brief_generator_v1' | 'post_mortem_v1'
    campaign_id: UUID
    extra_context: dict = {}


# ---------- Dashboard ----------

class DashboardKPIs(BaseModel):
    total_campaigns: int
    active_campaigns: int
    completed_campaigns: int
    total_clients: int
    total_brands: int
    total_influencers: int
    total_budget_usd: Decimal
    total_reach: int
    avg_engagement_rate: Decimal | None


# Resolve forward refs
CampaignDetail.model_rebuild()