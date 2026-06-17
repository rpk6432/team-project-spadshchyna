from fastapi import APIRouter, Query

from auth.dependencies import DBSession, OptionalUser
from homesteads import service
from homesteads.filters import HomesteadFilters
from homesteads.schemas import (
    AvailabilityRequest,
    AvailabilityResponse,
    HomesteadCard,
    HomesteadDetail,
    RegionResponse,
)
from schemas.common import PaginatedResponse

homestead_router = APIRouter(prefix="/homesteads", tags=["Homesteads"])
region_router = APIRouter(prefix="/regions", tags=["Regions"])

ERROR_400 = {"description": "Invalid request (business rule violation)"}
ERROR_404 = {"description": "Homestead not found"}
ERROR_422 = {"description": "Validation error (invalid input)"}


@homestead_router.get(
    "",
    summary="Browse homesteads catalog",
    response_model=PaginatedResponse[HomesteadCard],
    responses={200: {"description": "Paginated list of homesteads"}},
)
async def catalog(
    db: DBSession,
    user: OptionalUser,
    region_id: int | None = Query(None, description="Filter by region"),
    price_min: int | None = Query(None, ge=0, description="Minimum price per night"),
    price_max: int | None = Query(None, ge=0, description="Maximum price per night"),
    rating_min: float | None = Query(None, ge=0, le=5, description="Minimum rating"),
    guests: int | None = Query(None, ge=1, description="Minimum guest capacity"),
    limit: int = Query(12, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> PaginatedResponse[HomesteadCard]:
    """Return a paginated list of active homesteads with optional filters."""
    filters = HomesteadFilters(
        region_id=region_id,
        price_min=price_min,
        price_max=price_max,
        rating_min=rating_min,
        guests=guests,
        limit=limit,
        offset=offset,
    )
    user_id = user.id if user else None
    items, total = await service.get_catalog(db, filters, user_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@homestead_router.get(
    "/{homestead_id}",
    summary="Get homestead details",
    response_model=HomesteadDetail,
    responses={
        200: {"description": "Full homestead details"},
        404: ERROR_404,
    },
)
async def detail(
    homestead_id: int, db: DBSession, user: OptionalUser
) -> HomesteadDetail:
    """Return full homestead details including host, photos, amenities, and reviews."""
    user_id = user.id if user else None
    return await service.get_detail(db, homestead_id, user_id)


@homestead_router.post(
    "/{homestead_id}/check-availability",
    summary="Check availability and price",
    response_model=AvailabilityResponse,
    responses={
        200: {"description": "Availability status and price breakdown"},
        400: ERROR_400,
        404: ERROR_404,
        422: ERROR_422,
    },
)
async def check_availability(
    homestead_id: int, body: AvailabilityRequest, db: DBSession
) -> AvailabilityResponse:
    """Validate dates and guest count, return availability and price breakdown."""
    return await service.check_availability(db, homestead_id, body)


@homestead_router.get(
    "/{homestead_id}/recommendations",
    summary="Get recommendations",
    response_model=list[HomesteadCard],
    responses={
        200: {"description": "List of recommended homesteads"},
        404: ERROR_404,
    },
)
async def recommendations(
    homestead_id: int, db: DBSession, user: OptionalUser
) -> list[HomesteadCard]:
    """Return up to 4 random active homesteads, excluding the current one."""
    user_id = user.id if user else None
    return await service.get_recommendations(db, homestead_id, user_id)


@region_router.get(
    "",
    summary="List all regions",
    response_model=list[RegionResponse],
    responses={200: {"description": "List of all regions"}},
)
async def regions(db: DBSession) -> list[RegionResponse]:
    """Return all regions for the filter dropdown."""
    return await service.get_regions(db)
