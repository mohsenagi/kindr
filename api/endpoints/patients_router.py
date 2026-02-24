"""Patient endpoints module."""

from fastapi import APIRouter

from data_models.problem_details_exceptions import NotImplementedApiException


patients_router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@patients_router.get("/{phone_number}")
async def get_patient_by_phone(phone_number: str):
    """Lookup patient by phone number."""
    raise NotImplementedApiException(detail=f"Patient lookup not implemented yet for {phone_number}")
