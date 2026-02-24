"""Global exception handling middleware for uniform JSON errors."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from data_models.problem_details_exceptions import (
    InternalServerErrorException,
    ProblemDetailsException,
)


logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, call_next):
    """Handle all exceptions in one place and return JSON responses."""
    try:
        return await call_next(request)
    except ProblemDetailsException as exc:
        logger.info("Handled API exception", extra={"status_code": exc.http_status_code, "title": exc.title})
        return JSONResponse(status_code=exc.http_status_code, content=exc.to_api_response().model_dump())
    except Exception:
        logger.exception("Unhandled exception")
        fallback = InternalServerErrorException()
        return JSONResponse(status_code=fallback.http_status_code, content=fallback.to_api_response().model_dump())
