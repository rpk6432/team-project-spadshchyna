from fastapi import APIRouter, status

from auth.dependencies import CurrentUser, DBSession
from favourites import service
from homesteads.schemas import HomesteadCard
from schemas.common import MessageResponse
from schemas.docs import ERROR_401, ERROR_404, ERROR_409

router = APIRouter(prefix="/favourites", tags=["Favourites"])


@router.post(
    "/{homestead_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add to favourites",
    response_model=MessageResponse,
    responses={
        401: ERROR_401,
        404: ERROR_404,
        409: ERROR_409,
    },
)
async def add_favourite(
    homestead_id: int, user: CurrentUser, db: DBSession
) -> MessageResponse:
    """Add a homestead to the current user's favourites."""
    await service.add_favourite(db, user.id, homestead_id)
    return MessageResponse(detail="Added to favourites")


@router.delete(
    "/{homestead_id}",
    summary="Remove from favourites",
    response_model=MessageResponse,
    responses={
        401: ERROR_401,
        404: ERROR_404,
    },
)
async def remove_favourite(
    homestead_id: int, user: CurrentUser, db: DBSession
) -> MessageResponse:
    """Remove a homestead from the current user's favourites."""
    await service.remove_favourite(db, user.id, homestead_id)
    return MessageResponse(detail="Removed from favourites")


@router.get(
    "",
    summary="List favourites",
    response_model=list[HomesteadCard],
    responses={401: ERROR_401},
)
async def list_favourites(user: CurrentUser, db: DBSession) -> list[HomesteadCard]:
    """Return all homesteads in the current user's favourites."""
    return await service.get_favourites(db, user.id)
