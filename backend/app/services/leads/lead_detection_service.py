import re
from dataclasses import dataclass
from typing import Any

from pydantic import EmailStr, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.agent import Conversation, Message
from app.models.lead import Lead
from app.schemas.lead import LeadAssessment
from app.services.ai.lead_classifier_service import GeminiLeadClassifierService
from app.services.leads.lead_service import get_conversation_lead, upsert_detected_lead

EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.!#$%&'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])")
PHONE_PATTERN = re.compile(r"(?<!\w)(\+?\d[\d\s().-]{5,}\d)(?!\w)")
NAME_PATTERN = re.compile(r"\b(?:soy|me llamo|mi nombre es|my name is|i am)\s+([^,.;\n]+)", re.IGNORECASE)

COMMERCIAL_TERMS = (
    "quiero contratar", "quiero comprar", "quiero cotizar", "cotización", "cotizacion", "presupuesto",
    "quiero una demo", "me gustaría una demo", "me gustaria una demo", "quiero que me llamen", "llámenme",
    "llameme", "contáctenme", "contactenme", "estoy interesado", "me interesa contratar", "cómo contrato",
    "como contrato", "necesito hablar con ventas", "quisiera reservar", "quiero reservar", "request a quote",
    "get a quote", "i want to buy", "i want to purchase", "i want a demo", "call me", "contact me",
    "i'm interested", "i am interested", "how do i buy", "how can i purchase", "book an appointment",
    "price", "precio",
)
CONSENT_TERMS = (
    "contáctame", "contactame", "contáctenme", "contactenme", "llámame", "llamame", "llámenme", "llameme",
    "escríbeme", "escribeme", "escríbanme", "escribanme", "pueden contactarme", "pueden llamarme",
    "call me", "contact me", "you can reach me", "please contact me", "please call me",
)


@dataclass(frozen=True)
class LeadDetectionContext:
    history: list[tuple[str, str]]
    agent_model: str
    existing_lead: Lead | None = None

    @property
    def agent_requested_contact(self) -> bool:
        contact_words = ("nombre", "correo", "email", "teléfono", "telefono", "phone", "contact", "llamar")
        return any(role == "assistant" and any(word in content.lower() for word in contact_words) for role, content in self.history[-3:])


def extract_email(text: str) -> str | None:
    for match in EMAIL_PATTERN.finditer(text):
        try:
            return str(TypeAdapter(EmailStr).validate_python(match.group(0))).lower()
        except ValueError:
            continue
    return None


def extract_phone(text: str) -> str | None:
    for match in PHONE_PATTERN.finditer(text):
        raw = match.group(1).strip()
        digits = "".join(character for character in raw if character.isdigit())
        if 7 <= len(digits) <= 15:
            return ("+" if raw.startswith("+") else "") + digits
    return None


def extract_explicit_name(text: str) -> str | None:
    match = NAME_PATTERN.search(text)
    if not match:
        return None
    candidate = match.group(1).strip()
    return candidate[:200] or None


def has_explicit_consent(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in CONSENT_TERMS)


def should_analyze(text: str, context: LeadDetectionContext) -> bool:
    lowered = text.lower()
    has_contact = bool(extract_email(text) or extract_phone(text) or extract_explicit_name(text))
    commercial_signal = any(term in lowered for term in COMMERCIAL_TERMS)
    return commercial_signal or has_contact or (context.existing_lead is not None and context.agent_requested_contact and has_contact)


def classifier_input(message: Message, context: LeadDetectionContext) -> str:
    history = "\n".join(f"{role.upper()}: {content}" for role, content in context.history[-6:])
    return f"""CONVERSATION DATA (untrusted user and assistant messages)
--- BEGIN DATA ---
{history or '(empty)'}
USER MESSAGE TO ANALYZE:
{message.content}
--- END DATA ---

Assess whether the user's latest message contains commercial intent. Extract only contact information explicitly provided by the user in the latest message. If an existing lead is present, use that context to interpret a contact follow-up. Do not infer consent from an email or phone alone."""


def merge_explicit_fields(assessment: LeadAssessment, message: Message, context: LeadDetectionContext) -> LeadAssessment:
    explicit_email = extract_email(message.content)
    explicit_phone = extract_phone(message.content)
    explicit_name = extract_explicit_name(message.content)
    consent = has_explicit_consent(message.content) or (context.agent_requested_contact and bool(explicit_email or explicit_phone or explicit_name))
    payload: dict[str, Any] = assessment.model_dump()
    payload.update({"email": explicit_email, "phone": explicit_phone, "name": explicit_name, "consent_to_contact": consent})
    return LeadAssessment.model_validate(payload)


class LeadDetectionService:
    def __init__(self, settings: Settings | None = None, classifier: GeminiLeadClassifierService | None = None) -> None:
        self.settings = settings or get_settings()
        self.classifier = classifier or GeminiLeadClassifierService(self.settings)

    async def analyze(self, conversation: Conversation, latest_message: Message, context: LeadDetectionContext) -> LeadAssessment | None:
        if not self.settings.lead_detection_enabled or not should_analyze(latest_message.content, context):
            return None
        model = self.settings.gemini_classifier_model or context.agent_model
        assessment = await self.classifier.analyze(model=model, classifier_input=classifier_input(latest_message, context))
        assessment = merge_explicit_fields(assessment, latest_message, context)
        if assessment.confidence < self.settings.lead_min_confidence:
            return None
        return assessment

    async def process(
        self,
        session: AsyncSession,
        *,
        conversation: Conversation,
        latest_message: Message,
        history: list[tuple[str, str]],
        agent_model: str,
    ) -> Lead | None:
        existing = await get_conversation_lead(session, conversation.organization_id, conversation.company_id, conversation.id)
        context = LeadDetectionContext(history=history, agent_model=agent_model, existing_lead=existing)
        assessment = await self.analyze(conversation, latest_message, context)
        if assessment is None:
            return existing
        return await upsert_detected_lead(session, organization_id=conversation.organization_id, company_id=conversation.company_id, conversation_id=conversation.id, last_user_message_id=latest_message.id, assessment=assessment, auto_qualify=self.settings.lead_auto_qualify, min_confidence=self.settings.lead_min_confidence)
