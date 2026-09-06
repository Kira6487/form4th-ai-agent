import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import Settings
from app.models.agent import AIAgent, Conversation, Message
from app.models.lead import Lead
from app.schemas.lead import LeadAssessment
from app.services.ai.lead_classifier_service import GeminiLeadClassifierService, LeadClassifierError
from app.services.chat_service import answer_message, create_conversation
from app.services.leads.lead_detection_service import LeadDetectionContext, LeadDetectionService, extract_email, extract_explicit_name, extract_phone, has_explicit_consent, should_analyze
from app.services.leads.lead_service import LeadError, upsert_detected_lead
from app.services.rag.retrieval_service import RetrievedChunk


def assessment(**overrides) -> LeadAssessment:
    values = {
        "has_commercial_intent": True,
        "intent": "request_quote",
        "confidence": 0.91,
        "interest": "Business plan",
        "name": None,
        "email": None,
        "phone": None,
        "consent_to_contact": False,
        "missing_fields": ["email", "phone"],
    }
    values.update(overrides)
    return LeadAssessment.model_validate(values)


def test_prefilter_and_explicit_contact_extraction() -> None:
    context = LeadDetectionContext(history=[], agent_model="test-model")
    assert not should_analyze("Hola", context)
    assert not should_analyze("¿Dónde están ubicados?", context)
    assert should_analyze("Quiero una cotización", context)
    assert should_analyze("Soy Juan Pérez, mi correo es juan@example.com", context)
    assert extract_explicit_name("Soy Juan Pérez, mi correo es juan@example.com") == "Juan Pérez"
    assert extract_email("Mi correo es Juan@Example.com") == "juan@example.com"
    assert extract_phone("Mi teléfono es +51 999 888 777") == "+51999888777"
    assert not has_explicit_consent("Mi correo es juan@example.com")
    assert has_explicit_consent("Sí, escríbanme a juan@example.com")


class FakeInteractions:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output)


@pytest.mark.asyncio
async def test_classifier_uses_structured_response_format_and_validates() -> None:
    output = assessment(email="juan@example.com").model_dump_json()
    interactions = FakeInteractions(output)
    service = GeminiLeadClassifierService(Settings(_env_file=None, gemini_api_key="test-key"), SimpleNamespace(aio=SimpleNamespace(interactions=interactions)))
    result = await service.analyze(model="test-model", classifier_input="commercial message")
    request = interactions.calls[0]
    assert result.email == "juan@example.com"
    assert request["store"] is False
    assert request["response_format"]["type"] == "text"
    assert request["response_format"]["mime_type"] == "application/json"
    assert "properties" in request["response_format"]["schema"]

    invalid = GeminiLeadClassifierService(Settings(_env_file=None, gemini_api_key="test-key"), SimpleNamespace(aio=SimpleNamespace(interactions=FakeInteractions("not json"))))
    with pytest.raises(LeadClassifierError):
        await invalid.analyze(model="test-model", classifier_input="commercial message")


def test_assessment_rejects_invalid_enum_confidence_and_phone() -> None:
    with pytest.raises(ValidationError):
        assessment(intent="made_up_intent")
    with pytest.raises(ValidationError):
        assessment(confidence=1.1)
    with pytest.raises(ValidationError):
        assessment(phone="123")


@pytest.mark.asyncio
async def test_detection_prefilter_and_consent_are_contextual() -> None:
    class Classifier:
        def __init__(self) -> None:
            self.calls = 0

        async def analyze(self, **kwargs):
            self.calls += 1
            return assessment(email="juan@example.com", missing_fields=[])

    classifier = Classifier()
    service = LeadDetectionService(Settings(_env_file=None), classifier=classifier)
    conversation = Conversation(id=uuid4(), organization_id=uuid4(), company_id=uuid4(), agent_id=uuid4())
    hello = Message(conversation_id=conversation.id, organization_id=conversation.organization_id, company_id=conversation.company_id, role="user", content="Hola")
    context = LeadDetectionContext(history=[], agent_model="test-model")
    assert await service.analyze(conversation, hello, context) is None
    assert classifier.calls == 0

    contact = Message(conversation_id=conversation.id, organization_id=conversation.organization_id, company_id=conversation.company_id, role="user", content="Sí, escríbanme a juan@example.com")
    result = await service.analyze(conversation, contact, context)
    assert result is not None and result.email == "juan@example.com" and result.consent_to_contact is True
    assert classifier.calls == 1


def test_classifier_failure_does_not_fail_chat(tenant_client) -> None:
    from app.services.agent_service import create_agent
    from app.schemas.agent import AIAgentCreate
    from tests.test_knowledge_ingestion import seed_knowledge_tenants

    _, session_factory = tenant_client
    user_a, _, org_a, _, company_a, _ = seed_knowledge_tenants(session_factory)

    class Provider:
        provider_name = "gemini"

        async def generate_response(self, **kwargs):
            return SimpleNamespace(text="Answer remains available", model="test-model", latency_ms=2, usage=SimpleNamespace(input_tokens=2, output_tokens=3))

    class BrokenDetector:
        async def process(self, **kwargs):
            raise RuntimeError("classifier unavailable")

    async def run():
        async with session_factory() as session:
            agent_obj = await create_agent(session, org_a.id, company_a.id, AIAgentCreate(name="Sales", role="Assistant", objective="Answer", tone="Professional", language="English", system_instructions="Use knowledge.", status="active"))
            conversation = await create_conversation(session, org_a.id, company_a.id, agent_obj.id, user_a.id)
        chunk = RetrievedChunk(uuid4(), uuid4(), uuid4(), "Pricing", "Pricing is available.", 0.9, None, {})

        async def retrieval(*args, **kwargs):
            return [chunk]

        async with session_factory() as session:
            result = await answer_message(session, org_a.id, company_a.id, conversation.id, "Quiero una cotización", Settings(_env_file=None), retrieval=retrieval, provider=Provider(), lead_detector=BrokenDetector())
            lead = await session.scalar(select(Lead).where(Lead.conversation_id == conversation.id))
            return result, lead

    result, lead = asyncio.run(run())
    assert result.answer == "Answer remains available"
    assert lead is None


def test_lead_qualification_update_and_idempotency(tenant_client) -> None:
    from tests.test_knowledge_ingestion import seed_knowledge_tenants

    _, session_factory = tenant_client
    user_a, _, org_a, _, company_a, _ = seed_knowledge_tenants(session_factory)

    async def run():
        async with session_factory() as session:
            agent = AIAgent(organization_id=org_a.id, company_id=company_a.id, name="Sales", role="Sales assistant", objective="Detect interest", tone="Helpful", language="English", system_instructions="Do not invent facts", model="test-model", status="active")
            conversation = Conversation(organization_id=org_a.id, company_id=company_a.id, agent=agent, created_by=user_a.id)
            session.add(conversation)
            await session.flush()
            first_message = Message(organization_id=org_a.id, company_id=company_a.id, conversation_id=conversation.id, role="user", content="I want a quote")
            session.add(first_message)
            await session.commit()
            first = await upsert_detected_lead(session, organization_id=org_a.id, company_id=company_a.id, conversation_id=conversation.id, last_user_message_id=first_message.id, assessment=assessment(), auto_qualify=True)
            first_id, first_status = first.id, first.status
            second_message = Message(organization_id=org_a.id, company_id=company_a.id, conversation_id=conversation.id, role="user", content="I am Juan, juan@example.com")
            session.add(second_message)
            await session.commit()
            second = await upsert_detected_lead(session, organization_id=org_a.id, company_id=company_a.id, conversation_id=conversation.id, last_user_message_id=second_message.id, assessment=assessment(name="Juan", email="juan@example.com", missing_fields=[], consent_to_contact=False), auto_qualify=True)
            repeated = await upsert_detected_lead(session, organization_id=org_a.id, company_id=company_a.id, conversation_id=conversation.id, last_user_message_id=second_message.id, assessment=assessment(name="Juan", email="juan@example.com", missing_fields=[], consent_to_contact=False), auto_qualify=True)
            return first_id, first_status, second, repeated, list(await session.scalars(select(Lead).where(Lead.conversation_id == conversation.id)))

    first_id, first_status, second, repeated, leads = asyncio.run(run())
    assert first_status == "new"
    assert second is not None and second.id == first_id and second.status == "qualified"
    assert repeated is not None and repeated.id == first_id
    assert len(leads) == 1
    assert second.consent_to_contact is False


def test_lead_tenant_isolation_and_admin_update(tenant_client) -> None:
    from app.core.auth import get_current_user
    from app.main import app
    from tests.test_knowledge_ingestion import seed_knowledge_tenants

    client, session_factory = tenant_client
    user_a, user_b, org_a, org_b, company_a, company_b = seed_knowledge_tenants(session_factory)

    async def create_fixture():
        async with session_factory() as session:
            agent = AIAgent(organization_id=org_a.id, company_id=company_a.id, name="Sales", role="Sales assistant", objective="Detect interest", tone="Helpful", language="English", system_instructions="Use knowledge", model="test-model", status="active")
            conversation = Conversation(organization_id=org_a.id, company_id=company_a.id, agent=agent)
            session.add(conversation)
            await session.flush()
            message = Message(organization_id=org_a.id, company_id=company_a.id, conversation_id=conversation.id, role="user", content="I want a demo")
            session.add(message)
            await session.commit()
            lead = await upsert_detected_lead(session, organization_id=org_a.id, company_id=company_a.id, conversation_id=conversation.id, last_user_message_id=message.id, assessment=assessment(intent="request_demo", interest="Demo", missing_fields=["email"]), auto_qualify=True)
            return lead, conversation.id, message.id

    lead, conversation_id, message_id = asyncio.run(create_fixture())
    async def verify_conversation_ownership():
        async with session_factory() as session:
            with pytest.raises(LeadError, match="Conversation not found"):
                await upsert_detected_lead(session, organization_id=org_b.id, company_id=company_b.id, conversation_id=conversation_id, last_user_message_id=message_id, assessment=assessment(intent="request_demo", interest="Demo"), auto_qualify=True)

    asyncio.run(verify_conversation_ownership())
    app.dependency_overrides[get_current_user] = lambda: user_b
    assert client.get(f"/api/v1/organizations/{org_b.id}/companies/{company_b.id}/leads/{lead.id}").status_code == 404
    assert client.patch(f"/api/v1/organizations/{org_b.id}/companies/{company_b.id}/leads/{lead.id}", json={"status": "lost"}).status_code == 404
    assert client.get(f"/api/v1/organizations/{org_b.id}/companies/{company_b.id}/leads").json()["total"] == 0
    app.dependency_overrides[get_current_user] = lambda: user_a
    updated = client.patch(f"/api/v1/organizations/{org_a.id}/companies/{company_a.id}/leads/{lead.id}", json={"status": "qualified", "email": "juan@example.com"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "qualified"
