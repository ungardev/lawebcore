"""SQLAlchemy ORM models for La Web Core."""

from app.models.ai import (
    AIConversation,
    AIJob,
    AIMessage,
    AIPrompt,
    Document,
    DocumentChunk,
    Notification,
)
from app.models.analytics import (
    AuditLog,
    Dashboard,
    Export,
    Integration,
    ScheduledReport,
    Webhook,
    Widget,
)
from app.models.base import Base
from app.models.campaign import (
    Campaign,
    CampaignDocument,
    CampaignInfluencer,
    CampaignLink,
    CampaignStatusHistory,
)
from app.models.comentario import Comentario
from app.models.commercial import Brand, BrandContact, Client, ClientContract
from app.models.influencer import Influencer, InfluencerMetricsSnapshot, InfluencerSocialAccount
from app.models.kpi import Benchmark, CampaignKPIValue, Insight, KPIDefinition, WinningFormat
from app.models.operation import (
    Automation,
    AutomationLog,
    Budget,
    BudgetItem,
    Form,
    FormSubmission,
    Task,
)
from app.models.publicacion import Publicacion
from app.models.user import BusinessUnit, Permission, Role, Team, TeamMember, User, UserRole

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
