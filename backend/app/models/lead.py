import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

json_type = JSON().with_variant(JSONB(), "postgresql")


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("intent IN ('general_inquiry', 'purchase_interest', 'request_quote', 'request_demo', 'contact_request', 'appointment_interest', 'other_commercial')", name="ck_leads_intent"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_leads_confidence"),
        CheckConstraint("status IN ('new', 'qualified', 'contacted', 'converted', 'lost')", name="ck_leads_status"),
        CheckConstraint("source IN ('dashboard_test', 'widget', 'whatsapp', 'email', 'api')", name="ck_leads_source"),
        Index("ix_leads_organization_id", "organization_id"),
        Index("ix_leads_company_id", "company_id"),
        Index("ix_leads_status", "status"),
        Index("ix_leads_intent", "intent"),
        Index("ix_leads_source", "source"),
        Index("ux_leads_conversation_id", "conversation_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_agents.id", ondelete="SET NULL"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(32))
    interest: Mapped[str | None] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="dashboard_test")
    consent_to_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_user_message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    lead_metadata: Mapped[dict | None] = mapped_column("metadata", json_type)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    conversation = relationship("Conversation", back_populates="lead")
