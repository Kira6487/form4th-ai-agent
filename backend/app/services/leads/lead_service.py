import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AIAgent, Conversation, Message
from app.models.lead import Lead
from app.schemas.lead import LeadAssessment

logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "new": {"new", "qualified", "lost"},
    "qualified": {"qualified", "contacted", "lost", "new"},
    "contacted": {"contacted", "converted", "lost", "qualified"},
    "converted": {"converted", "contacted"},
    "lost": {"lost", "new"},
}


class LeadError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


async def get_lead(session: AsyncSession, organization_id: UUID, company_id: UUID, lead_id: UUID) -> Lead | None:
    return await session.scalar(select(Lead).where(Lead.id == lead_id, Lead.organization_id == organization_id, Lead.company_id == company_id))


async def get_conversation_lead(session: AsyncSession, organization_id: UUID, company_id: UUID, conversation_id: UUID) -> Lead | None:
    return await session.scalar(select(Lead).where(Lead.conversation_id == conversation_id, Lead.organization_id == organization_id, Lead.company_id == company_id))


async def list_leads(
    session: AsyncSession,
    organization_id: UUID,
    company_id: UUID,
    *,
    status: str | None = None,
    intent: str | None = None,
    source: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[Lead], int]:
    filters: list[Any] = [Lead.organization_id == organization_id, Lead.company_id == company_id]
    if status:
        filters.append(Lead.status == status)
    if intent:
        filters.append(Lead.intent == intent)
    if source:
        filters.append(Lead.source == source)
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Lead.name.ilike(term), Lead.email.ilike(term)))
    total = await session.scalar(select(func.count()).select_from(Lead).where(*filters)) or 0
    items = list(await session.scalars(select(Lead).where(*filters).order_by(Lead.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
    return items, int(total)


def lead_qualifies(lead: Lead) -> bool:
    return lead.intent != "general_inquiry" and bool(lead.interest) and bool(lead.email or lead.phone)


async def upsert_detected_lead(
    session: AsyncSession,
    *,
    organization_id: UUID,
    company_id: UUID,
    conversation_id: UUID,
    last_user_message_id: UUID,
    assessment: LeadAssessment,
    auto_qualify: bool,
    min_confidence: float = 0.70,
    source: str = "dashboard_test",
) -> Lead | None:
    relation = await session.execute(
        select(Conversation, AIAgent)
        .join(AIAgent, AIAgent.id == Conversation.agent_id)
        .where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
            Conversation.company_id == company_id,
            AIAgent.organization_id == organization_id,
            AIAgent.company_id == company_id,
        )
    )
    pair = relation.first()
    if pair is None:
        raise LeadError("conversation_not_found", "Conversation not found")
    message = await session.scalar(select(Message).where(Message.id == last_user_message_id, Message.conversation_id == conversation_id, Message.organization_id == organization_id, Message.company_id == company_id, Message.role == "user"))
    if message is None:
        raise LeadError("message_not_found", "User message not found")
    existing = await get_conversation_lead(session, organization_id, company_id, conversation_id)
    if existing and existing.last_user_message_id == last_user_message_id:
        return existing
    if assessment.confidence < min_confidence:
        return existing
    if not assessment.has_commercial_intent or assessment.intent == "general_inquiry":
        if existing and (assessment.name or assessment.email or assessment.phone):
            existing.name = assessment.name or existing.name
            existing.email = str(assessment.email) if assessment.email else existing.email
            existing.phone = assessment.phone or existing.phone
            existing.consent_to_contact = existing.consent_to_contact or assessment.consent_to_contact
            existing.last_user_message_id = last_user_message_id
            if auto_qualify and lead_qualifies(existing) and existing.status == "new":
                existing.status = "qualified"
                existing.qualified_at = existing.qualified_at or datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(existing)
            return existing
        return existing
    now = datetime.now(timezone.utc)
    if existing is None:
        lead = Lead(
            organization_id=organization_id,
            company_id=company_id,
            agent_id=pair[0].agent_id,
            conversation_id=conversation_id,
            name=assessment.name,
            email=str(assessment.email) if assessment.email else None,
            phone=assessment.phone,
            interest=assessment.interest,
            intent=assessment.intent,
            confidence=assessment.confidence,
            status="new",
            source=source,
            consent_to_contact=assessment.consent_to_contact,
            detected_at=now,
            last_user_message_id=last_user_message_id,
            lead_metadata={"missing_fields": assessment.missing_fields},
        )
        session.add(lead)
    else:
        lead = existing
        lead.name = assessment.name or lead.name
        lead.email = str(assessment.email) if assessment.email else lead.email
        lead.phone = assessment.phone or lead.phone
        lead.interest = assessment.interest or lead.interest
        if assessment.intent != "general_inquiry":
            lead.intent = assessment.intent
        lead.confidence = assessment.confidence
        lead.consent_to_contact = lead.consent_to_contact or assessment.consent_to_contact
        lead.detected_at = now
        lead.last_user_message_id = last_user_message_id
        lead.lead_metadata = {"missing_fields": assessment.missing_fields}

    await session.flush()
    if auto_qualify and lead_qualifies(lead) and lead.status == "new":
        lead.status = "qualified"
        lead.qualified_at = lead.qualified_at or now
    logger.info(
        "lead_detected",
        extra={
            "lead_id": str(lead.id),
            "organization_id": str(organization_id),
            "company_id": str(company_id),
            "conversation_id": str(conversation_id),
            "intent": lead.intent,
            "confidence": float(lead.confidence),
            "status": lead.status,
        },
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_conversation_lead(session, organization_id, company_id, conversation_id)
        if existing is not None:
            return existing
        raise
    await session.refresh(lead)
    return lead


async def update_lead(session: AsyncSession, lead: Lead, values: dict[str, Any]) -> Lead:
    requested_status = values.pop("status", None)
    if requested_status is not None and requested_status not in ALLOWED_TRANSITIONS.get(lead.status, set()):
        raise LeadError("invalid_status_transition", f"Cannot change lead status from {lead.status} to {requested_status}")
    for field, value in values.items():
        if field == "email" and value is not None:
            value = str(value)
        setattr(lead, field, value)
    if requested_status is not None:
        lead.status = requested_status
        if requested_status == "qualified" and lead.qualified_at is None:
            lead.qualified_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(lead)
    logger.info("lead_status_changed", extra={"lead_id": str(lead.id), "organization_id": str(lead.organization_id), "company_id": str(lead.company_id), "conversation_id": str(lead.conversation_id), "status": lead.status})
    return lead
