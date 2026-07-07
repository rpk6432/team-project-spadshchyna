from fastapi import APIRouter, status

from auth import service
from auth.dependencies import CurrentUser, DBSession
from auth.schemas import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
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


@router.post(
    "/forgot-password",
    summary="Request password reset",
    response_model=MessageResponse,
    responses={
        200: {"description": "If this email is registered, a reset code will be sent"},
        422: ERROR_422,
    },
)
async def forgot_password(
    body: ForgotPasswordRequest, db: DBSession
) -> MessageResponse:
    """
    Send a 6-digit reset code to the user's email.

    Always returns 200 regardless of whether the email exists.
    Cooldown: 15 seconds between requests for the same email.
    Code is valid for 10 minutes.
    """
    await service.forgot_password(db, body.email)
    return MessageResponse(
        detail="If this email is registered, a reset code will be sent"
    )


@router.post(
    "/reset-password",
    summary="Reset password",
    response_model=MessageResponse,
    responses={
        200: {"description": "Password has been reset"},
        400: {
            "description": "Bad request",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_code": {
                            "summary": "Invalid or expired code",
                            "value": {"detail": "Invalid or expired code"},
                        },
                        "too_many_attempts": {
                            "summary": "Too many attempts",
                            "value": {
                                "detail": "Too many attempts, request a new code"
                            },
                        },
                    }
                }
            },
        },
        422: ERROR_422,
    },
)
async def reset_password(body: ResetPasswordRequest, db: DBSession) -> MessageResponse:
    """
    Reset password using a 6-digit code from the reset email.

    Max 5 attempts per code. After 5 wrong attempts the code is
    invalidated and a new one must be requested.
    On success all existing sessions are revoked.
    """
    await service.reset_password(db, body.email, body.code, body.new_password)
    return MessageResponse(detail="Password has been reset")
