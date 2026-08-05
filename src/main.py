from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.sessions import SessionMiddleware

from admin.setup import setup_admin
from api.router import router as api_router
from config import settings
from core.exceptions import AppError
from core.redis import get_redis
from s3.client import ensure_bucket


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    await ensure_bucket()
    yield
    await get_redis().close()


app = FastAPI(title="Spadshchyna API", lifespan=lifespan)

_parsed = urlparse(settings.frontend_url)
_cors_origin = f"{_parsed.scheme}://{_parsed.netloc}"

app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(
    _request: Request, _exc: IntegrityError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "Resource already exists"},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
setup_admin(app)
