"""Custom exceptions for consistent API error handling."""

from data_models.responses import ProblemDetailsApiResponse, StandardApiError


class ProblemDetailsException(Exception):
    """Base exception that maps to a JSON API error response."""

    def __init__(
        self,
        http_status_code: int,
        title: str,
        code: str,
        detail: str,
        field: str | None = None,
        type_uri: str | None = None,
    ):
        self.http_status_code = http_status_code
        self.title = title
        self.code = code
        self.detail = detail
        self.field = field
        self.type_uri = type_uri
        super().__init__(detail)

    def to_api_response(self) -> ProblemDetailsApiResponse:
        """Convert exception to API error response model."""
        return ProblemDetailsApiResponse(
            title=self.title,
            type=self.type_uri,
            errors=[
                StandardApiError(
                    message=self.detail,
                    code=self.code,
                    field=self.field,
                )
            ],
        )


class BadRequestException(ProblemDetailsException):
    """HTTP 400 exception."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(400, "Bad Request", "BAD_REQUEST", detail)


class ValidationException(ProblemDetailsException):
    """HTTP 400 validation exception for request validation failures."""

    def __init__(self, detail: str = "Validation failed", field: str | None = None):
        super().__init__(400, "Validation Error", "VALIDATION_ERROR", detail, field=field)


class NotFoundException(ProblemDetailsException):
    """HTTP 404 exception."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(404, "Not Found", "NOT_FOUND", detail)


class ConflictException(ProblemDetailsException):
    """HTTP 409 exception."""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(409, "Conflict", "CONFLICT", detail)


class ServiceUnavailableException(ProblemDetailsException):
    """HTTP 503 exception."""

    def __init__(self, detail: str = "Service unavailable"):
        super().__init__(503, "Service Unavailable", "SERVICE_UNAVAILABLE", detail)


class GatewayTimeoutException(ProblemDetailsException):
    """HTTP 504 exception."""

    def __init__(self, detail: str = "Gateway timeout"):
        super().__init__(504, "Gateway Timeout", "GATEWAY_TIMEOUT", detail)


class InternalServerErrorException(ProblemDetailsException):
    """HTTP 500 exception."""

    def __init__(self, detail: str = "An unexpected error occurred"):
        super().__init__(500, "Internal Server Error", "INTERNAL_SERVER_ERROR", detail)


class NotImplementedApiException(ProblemDetailsException):
    """HTTP 501 exception for scaffold-only endpoints."""

    def __init__(self, detail: str = "Not implemented"):
        super().__init__(501, "Not Implemented", "NOT_IMPLEMENTED", detail)
