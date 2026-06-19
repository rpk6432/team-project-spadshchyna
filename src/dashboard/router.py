from fastapi import APIRouter

from auth.dependencies import CurrentUser, DBSession
from dashboard import service
from dashboard.schemas import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    summary="User dashboard",
    response_model=DashboardResponse,
    responses={401: {"description": "Not authenticated"}},
)
async def get_dashboard(user: CurrentUser, db: DBSession) -> DashboardResponse:
    """Return aggregated stats, upcoming stay, past journeys, and favourites."""
    return await service.get_dashboard(db, user.id)
