class AppError(Exception):
    """Base exception for all domain errors."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    """Resource not found."""

    status_code = 404
    detail = "Resource not found"


class AlreadyExistsError(AppError):
    """Resource already exists (unique constraint violation)."""

    status_code = 409
    detail = "Resource already exists"


class UnauthorizedError(AppError):
    """Authentication required or failed."""

    status_code = 401
    detail = "Not authenticated"


class ForbiddenError(AppError):
    """Insufficient permissions."""

    status_code = 403
    detail = "Forbidden"


class BadRequestError(AppError):
    """Business logic constraint violation."""

    status_code = 400
    detail = "Bad request"
