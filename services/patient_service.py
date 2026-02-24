"""Internal patient service.

Naming convention note:
- Class: PatientService
- File: patient_service.py
"""

from data_models.patient import PatientResponse
from data_models.problem_details_exceptions import BadRequestException, NotFoundException
from services.dental_track_api_query_service import DentalTrackApiQueryService


class PatientService:
    """Single-responsibility service for patient lookup workflows."""

    def __init__(self, api_query_service: DentalTrackApiQueryService | None = None):
        self.api_query_service = api_query_service or DentalTrackApiQueryService()
        self._patient_cache: dict[str, PatientResponse] = {}

    async def get_patient_by_phone(self, phone_number: str) -> PatientResponse:
        """Lookup patient by incoming phone number and return canonical patient data."""
        normalized_phone = self._normalize_phone_input(phone_number)

        cached_patient = self._patient_cache.get(normalized_phone)
        if cached_patient is not None:
            return cached_patient

        patient = await self.api_query_service.query_patient_by_phone(normalized_phone)
        if patient is None:
            raise NotFoundException("Patient not found")

        self._patient_cache[normalized_phone] = patient

        return patient

    @staticmethod
    def _normalize_phone_input(phone_number: str) -> str:
        digits = "".join(ch for ch in phone_number if ch.isdigit())
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]

        if len(digits) != 10:
            raise BadRequestException("Invalid phone number format")

        return digits
