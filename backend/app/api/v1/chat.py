import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import OrganizationContext, require_organization_member
from app.db.session import get_db_session
from app.schemas.agent import ChatMessageCreate, ChatResponse, ChatSource, ConversationCreate, ConversationRead, MessageRead
from app.schemas.lead import LeadSignal
from app.services.agent_service import get_agent
from app.services.chat_service import ChatError, answer_message, create_conversation, get_conversation, list_conversations, list_messages, stream_message

router = APIRouter(prefix="/organizations/{organization_id}/companies/{company_id}", tags=["chat"])


def _chat_error(exc: ChatError) -> HTTPException:
    codes = {"agent_not_found": 404, "conversation_not_found": 404, "agent_disabled": 409, "conversation_closed": 409, "message_too_large": 422, "retrieval_unavailable": 503, "provider_unavailable": 503}
    return HTTPException(status_code=codes.get(exc.code, 422), detail=str(exc))


@router.post("/agents/{agent_id}/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_chat_conversation(data: ConversationCreate, agent_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> ConversationRead:
    try:
        return ConversationRead.model_validate(await create_conversation(session, context.organization.id, company_id, agent_id, context.user.id, data.channel))
    except ChatError as exc:
        raise _chat_error(exc) from exc


@router.get("/agents/{agent_id}/conversations", response_model=list[ConversationRead])
async def conversations(agent_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> list[ConversationRead]:
    if await get_agent(session, context.organization.id, company_id, agent_id) is None:
        raise HTTPException(status_code=404, detail="AI agent not found")
    return [ConversationRead.model_validate(item) for item in await list_conversations(session, context.organization.id, company_id, agent_id)]


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
async def get_chat_conversation(conversation_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> ConversationRead:
    item = await get_conversation(session, context.organization.id, company_id, conversation_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationRead.model_validate(item)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
async def messages(conversation_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> list[MessageRead]:
    if await get_conversation(session, context.organization.id, company_id, conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [MessageRead.model_validate(item) for item in await list_messages(session, context.organization.id, company_id, conversation_id)]


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(data: ChatMessageCreate, conversation_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> ChatResponse:
    try:
        result = await answer_message(session, context.organization.id, company_id, conversation_id, data.message)
    except ChatError as exc:
        raise _chat_error(exc) from exc
    return ChatResponse(conversation_id=result.conversation.id, message_id=result.message.id, answer=result.answer, sources=[ChatSource(**source) for source in result.sources], model=result.model, lead=LeadSignal(id=result.lead.id, status=result.lead.status) if result.lead else None)


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(data: ChatMessageCreate, conversation_id: UUID, company_id: UUID, context: OrganizationContext = Depends(require_organization_member()), session: AsyncSession = Depends(get_db_session)) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        try:
            async for kind, payload in stream_message(session, context.organization.id, company_id, conversation_id, data.message):
                body = payload if isinstance(payload, dict) else {"text": payload}
                yield f"event: {kind}\ndata: {json.dumps(body)}\n\n"
        except ChatError as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
