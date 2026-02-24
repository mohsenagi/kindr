"""Standard API response models."""

from typing import Any

from pydantic import BaseModel


class StandardApiError(BaseModel):
    """Error payload used by problem-details style responses."""

    message: str
    code: str
    field: str | None = None


class ProblemDetailsApiResponse(BaseModel):
    """Error response envelope."""

    title: str
    errors: list[StandardApiError]
    type: str | None = None


class SuccessApiResponse(BaseModel):
    """Generic success envelope for future use."""

    data: Any
