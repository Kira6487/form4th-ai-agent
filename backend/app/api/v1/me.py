from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.schemas.auth import AuthenticatedUser, MeResponse

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=MeResponse)
async def me(user: AuthenticatedUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse.model_validate(user.model_dump())
