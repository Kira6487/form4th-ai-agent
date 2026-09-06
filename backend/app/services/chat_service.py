import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.agent import AIAgent, Conversation, Message
from app.models.company import Company
from app.services.agent_prompt_builder import build_agent_system_instruction, build_chat_input
from app.services.ai.conversation_service import ConversationProviderError, GeminiConversationService
from app.services.rag.context_builder import build_rag_context
from app.services.rag.retrieval_service import RetrievedChunk, search_knowledge

class ChatError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ChatResult:
    conversation: Conversation
    message: Message
    answer: str
    sources: list[dict]
    model: str | None


_locks: dict[UUID, asyncio.Lock] = {}


def _lock_for(conversation_id: UUID) -> asyncio.Lock:
    return _locks.setdefault(conversation_id, asyncio.Lock())


def _fallback_legacy(language: str) -> str:
    return _fallback(language)
    return "No encontré esa información en la base de conocimiento disponible." if language.lower().startswith(("es", "spa")) else "I could not find that information in the available knowledge base."


def _fallback(language: str) -> str:
    return "No encontr\u00e9 esa informaci\u00f3n en la base de conocimiento disponible." if language.lower().startswith(("es", "spa")) else "I could not find that information in the available knowledge base."


def _sources(items: list[RetrievedChunk]) -> list[dict]:
    return [{"source_id": str(item.source_id), "document_id": str(item.document_id), "chunk_id": str(item.chunk_id), "title": item.title, "url": item.source_url} for item in items]


async def _conversation(session: AsyncSession, organization_id: UUID, company_id: UUID, conversation_id: UUID) -> tuple[Conversation, AIAgent] | None:
    row = await session.execute(select(Conversation, AIAgent).join(AIAgent, AIAgent.id == Conversation.agent_id).where(Conversation.id == conversation_id, Conversation.organization_id == organization_id, Conversation.company_id == company_id, AIAgent.organization_id == organization_id, AIAgent.company_id == company_id))
    return row.first()


async def get_conversation(session: AsyncSession, organization_id: UUID, company_id: UUID, conversation_id: UUID) -> Conversation | None:
    return await session.scalar(select(Conversation).join(AIAgent, AIAgent.id == Conversation.agent_id).where(Conversation.id == conversation_id, Conversation.organization_id == organization_id, Conversation.company_id == company_id, AIAgent.organization_id == organization_id, AIAgent.company_id == company_id))


async def list_conversations(session: AsyncSession, organization_id: UUID, company_id: UUID, agent_id: UUID) -> list[Conversation]:
    return list(await session.scalars(select(Conversation).where(Conversation.organization_id == organization_id, Conversation.company_id == company_id, Conversation.agent_id == agent_id).order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc())))


async def list_messages(session: AsyncSession, organization_id: UUID, company_id: UUID, conversation_id: UUID) -> list[Message]:
    return list(await session.scalars(select(Message).where(Message.organization_id == organization_id, Message.company_id == company_id, Message.conversation_id == conversation_id, Message.status == "completed").order_by(Message.created_at.asc())))


async def create_conversation(session: AsyncSession, organization_id: UUID, company_id: UUID, agent_id: UUID, user_id: UUID, channel: str = "dashboard") -> Conversation:
    agent = await session.scalar(select(AIAgent).where(AIAgent.id == agent_id, AIAgent.organization_id == organization_id, AIAgent.company_id == company_id))
    if agent is None:
        raise ChatError("agent_not_found", "AI agent not found")
    if agent.status == "disabled":
        raise ChatError("agent_disabled", "AI agent is disabled")
    conversation = Conversation(organization_id=organization_id, company_id=company_id, agent_id=agent_id, created_by=user_id, channel=channel)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def _history(session: AsyncSession, conversation_id: UUID, max_messages: int) -> list[tuple[str, str]]:
    messages = list(await session.scalars(select(Message).where(Message.conversation_id == conversation_id, Message.status == "completed").order_by(Message.created_at.desc()).limit(max_messages)))
    return [(message.role, message.content) for message in reversed(messages)]


async def answer_message(
    session: AsyncSession,
    organization_id: UUID,
    company_id: UUID,
    conversation_id: UUID,
    user_message: str,
    settings: Settings | None = None,
    retrieval: Callable[..., Awaitable[list[RetrievedChunk]]] = search_knowledge,
    provider: GeminiConversationService | None = None,
) -> ChatResult:
    settings = settings or get_settings()
    if len(user_message) > settings.chat_max_message_chars:
        raise ChatError("message_too_large", "Message exceeds the configured limit")
    async with _lock_for(conversation_id):
        pair = await _conversation(session, organization_id, company_id, conversation_id)
        if pair is None:
            raise ChatError("conversation_not_found", "Conversation not found")
        conversation, agent = pair
        if agent.status == "disabled":
            raise ChatError("agent_disabled", "AI agent is disabled")
        if conversation.status != "active":
            raise ChatError("conversation_closed", "Conversation is closed")
        history = await _history(session, conversation.id, settings.chat_history_max_messages)
        session.add(Message(organization_id=organization_id, company_id=company_id, conversation_id=conversation.id, role="user", content=user_message, status="completed"))
        await session.flush()
        try:
            items = await retrieval(session, organization_id, company_id, user_message, settings=settings)
        except Exception as exc:
            await session.rollback()
            raise ChatError("retrieval_unavailable", "Knowledge retrieval is temporarily unavailable") from exc
        sources = _sources(items)
        if not items:
            answer = _fallback(agent.language)
            generated = None
        else:
            context = build_rag_context(items)[:settings.rag_max_context_chars]
            prompt = build_chat_input(history, user_message, context)
            try:
                company_name = await session.scalar(select(Company.name).where(Company.id == company_id)) or "the company"
                conversation_provider = provider or GeminiConversationService(settings)
                generated = await conversation_provider.generate_response(model=agent.model, system_instruction=build_agent_system_instruction(agent, company_name), user_input=prompt, temperature=float(agent.temperature) if agent.temperature is not None else None, max_output_tokens=agent.max_output_tokens)
            except ConversationProviderError as exc:
                await session.rollback()
                raise ChatError("provider_unavailable", "AI provider is temporarily unavailable") from exc
            answer = generated.text
        message = Message(organization_id=organization_id, company_id=company_id, conversation_id=conversation.id, role="assistant", content=answer, retrieved_chunk_ids=[str(item.chunk_id) for item in items], sources=sources, provider=conversation_provider.provider_name if generated else None, model=generated.model if generated else None, latency_ms=generated.latency_ms if generated else 0, input_tokens=generated.usage.input_tokens if generated else None, output_tokens=generated.usage.output_tokens if generated else None, status="completed")
        session.add(message)
        conversation.last_message_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(message)
        return ChatResult(conversation, message, answer, sources, generated.model if generated else None)


async def stream_message(
    session: AsyncSession, organization_id: UUID, company_id: UUID, conversation_id: UUID, user_message: str, settings: Settings | None = None, retrieval: Callable[..., Awaitable[list[RetrievedChunk]]] = search_knowledge, provider: GeminiConversationService | None = None,
) -> AsyncIterator[tuple[str, Any]]:
    """Yield visible text chunks and persist only after a complete stream."""
    settings = settings or get_settings()
    if len(user_message) > settings.chat_max_message_chars:
        raise ChatError("message_too_large", "Message exceeds the configured limit")
    async with _lock_for(conversation_id):
        pair = await _conversation(session, organization_id, company_id, conversation_id)
        if pair is None:
            raise ChatError("conversation_not_found", "Conversation not found")
        conversation, agent = pair
        if agent.status == "disabled":
            raise ChatError("agent_disabled", "AI agent is disabled")
        if conversation.status != "active":
            raise ChatError("conversation_closed", "Conversation is closed")
        history = await _history(session, conversation.id, settings.chat_history_max_messages)
        try:
            items = await retrieval(session, organization_id, company_id, user_message, settings=settings)
        except Exception as exc:
            await session.rollback()
            raise ChatError("retrieval_unavailable", "Knowledge retrieval is temporarily unavailable") from exc
        sources = _sources(items)
        if not items:
            answer = _fallback(agent.language)
            yield "text", answer
        else:
            context = build_rag_context(items)[:settings.rag_max_context_chars]
            prompt = build_chat_input(history, user_message, context)
            answer_parts: list[str] = []
            company_name = "the company"
            company_name = await session.scalar(select(Company.name).where(Company.id == company_id)) or company_name
            conversation_provider = provider or GeminiConversationService(settings)
            try:
                async for part in conversation_provider.stream_response(model=agent.model, system_instruction=build_agent_system_instruction(agent, company_name), user_input=prompt, temperature=float(agent.temperature) if agent.temperature is not None else None, max_output_tokens=agent.max_output_tokens):
                    answer_parts.append(part)
                    yield "text", part
            except ConversationProviderError as exc:
                await session.rollback()
                raise ChatError("provider_unavailable", "AI provider is temporarily unavailable") from exc
            answer = "".join(answer_parts).strip()
            if not answer:
                raise ChatError("provider_unavailable", "AI provider returned no visible answer")
        session.add(Message(organization_id=organization_id, company_id=company_id, conversation_id=conversation.id, role="user", content=user_message, status="completed"))
        session.add(Message(organization_id=organization_id, company_id=company_id, conversation_id=conversation.id, role="assistant", content=answer, retrieved_chunk_ids=[str(item.chunk_id) for item in items], sources=sources, provider=conversation_provider.provider_name if items else None, model=agent.model if items else None, status="completed"))
        conversation.last_message_at = datetime.now(timezone.utc)
        await session.commit()
        yield "done", {"sources": sources, "model": agent.model if items else None}
