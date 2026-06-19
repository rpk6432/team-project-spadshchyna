from fastapi import APIRouter, status

from auth import service
from auth.dependencies import CurrentUser, DBSession
from auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from schemas.common import MessageResponse
from schemas.docs import ERROR_401, ERROR_409, ERROR_422

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    response_model=TokenResponse,
    responses={
        201: {"description": "User created, tokens returned"},
        409: ERROR_409,
        422: ERROR_422,
    },
)
async def register(body: RegisterRequest, db: DBSession) -> TokenResponse:
    """Create a new user account and return a JWT token pair."""
    return await service.register(db, body)


@router.post(
    "/login",
    summary="Log in",
    response_model=TokenResponse,
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"description": "Invalid email or password"},
        422: ERROR_422,
    },
)
async def login(body: LoginRequest, db: DBSession) -> TokenResponse:
    """Authenticate with email and password, receive a JWT token pair."""
    return await service.login(db, body)


@router.post(
    "/refresh",
    summary="Refresh access token",
    response_model=AccessTokenResponse,
    responses={
        200: {"description": "New access token returned"},
        401: {"description": "Invalid or expired refresh token"},
        422: ERROR_422,
    },
)
async def refresh(body: RefreshRequest) -> AccessTokenResponse:
    """Exchange a valid refresh token for a new access token."""
    return await service.refresh(body)


@router.post(
    "/logout",
    summary="Log out",
    response_model=MessageResponse,
    responses={
        200: {"description": "Successfully logged out"},
        401: ERROR_401,
        422: ERROR_422,
    },
)
async def logout(body: RefreshRequest, user: CurrentUser) -> MessageResponse:
    """Invalidate a refresh token, ending the session."""
    await service.logout(body.refresh_token)
    return MessageResponse(detail="Logged out")


@router.get(
    "/me",
    summary="Get current user",
    response_model=UserResponse,
    responses={
        200: {"description": "Current user profile"},
        401: ERROR_401,
    },
)
async def me(user: CurrentUser) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        is_admin=user.is_admin,
    )
