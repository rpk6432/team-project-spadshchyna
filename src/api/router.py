from fastapi import APIRouter

from auth.router import router as auth_router
from dashboard.router import router as dashboard_router
from favourites.router import router as favourites_router
from homesteads.router import homestead_router, region_router
from payments.router import router as payments_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(favourites_router)
router.include_router(homestead_router)
router.include_router(payments_router)
router.include_router(region_router)
