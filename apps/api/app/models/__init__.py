"""SQLAlchemy ORM models for La Web Core."""

from app.models.base import Base
from app.models.user import User, Role, Permission, UserRole, BusinessUnit, Team, TeamMember
from app.models.commercial import Client, Brand, BrandContact, ClientContract
from app.models.influencer import Influencer, InfluencerSocialAccount, InfluencerMetricsSnapshot
from app.models.campaign import (
    Campaign,
    CampaignStatusHistory,
    CampaignInfluencer,
    CampaignLink,
    CampaignDocument,
)
from app.models.kpi import KPIDefinition, CampaignKPIValue, Benchmark, Insight, WinningFormat
from app.models.operation import (
    Budget,
    BudgetItem,
    Task,
    Form,
    FormSubmission,
    Automation,
    AutomationLog,
)
from app.models.ai import (
    AIPrompt,
    Document,
    DocumentChunk,
    AIConversation,
    AIMessage,
    AIJob,
    Notification,
)
from app.models.analytics import (
    Dashboard,
    Widget,
    ScheduledReport,
    AuditLog,
    Integration,
    Webhook,
    Export,
)
from app.models.publicacion import Publicacion
from app.models.comentario import Comentario

__all__ = [
    "Base",
    # Identity
    "User", "Role", "Permission", "UserRole", "BusinessUnit", "Team", "TeamMember",
    # Commercial
    "Client", "Brand", "BrandContact", "ClientContract",
    # Influencers
    "Influencer", "InfluencerSocialAccount", "InfluencerMetricsSnapshot",
    # Campaigns
    "Campaign", "CampaignStatusHistory", "CampaignInfluencer", "CampaignLink", "CampaignDocument",
    # KPIs
    "KPIDefinition", "CampaignKPIValue", "Benchmark", "Insight", "WinningFormat",
    # Operations
    "Budget", "BudgetItem", "Task", "Form", "FormSubmission", "Automation", "AutomationLog",
    # AI
    "AIPrompt", "Document", "DocumentChunk", "AIConversation", "AIMessage", "AIJob", "Notification",
    # Analytics
    "Dashboard", "Widget", "ScheduledReport", "AuditLog", "Integration", "Webhook", "Export",
    # P.I.A.R
    "Publicacion", "Comentario",
]