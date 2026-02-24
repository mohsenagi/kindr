"""Patient endpoints module."""

from fastapi import APIRouter

from data_models.patient import PatientResponse
from services.patient_service import PatientService


patients_router = APIRouter(prefix="/api/v1/patients", tags=["patients"])
patient_service = PatientService()


@patients_router.get("/{phone_number}")
async def get_patient_by_phone(phone_number: str) -> PatientResponse:
    """Lookup patient by phone number."""
    return await patient_service.get_patient_by_phone(phone_number)
