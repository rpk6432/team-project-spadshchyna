from fastapi import APIRouter

from auth.router import router as auth_router
from homesteads.router import homestead_router, region_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(homestead_router)
router.include_router(region_router)
