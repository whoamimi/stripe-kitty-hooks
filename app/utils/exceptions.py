# app/utils/exceptions.py


from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from ..utils.woodlogs import get_logger

logger = get_logger(__name__)

async def internal_error_handler(request: Request, exc: Exception):
    """Handle unexpected server errors."""
    logger.exception(
        f"Unhandled server error: {exc.__class__.__name__}",
        extra={
            "path": request.url.path,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "type": "internal_error"
        },
    )