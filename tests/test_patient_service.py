"""Unit tests for PatientService."""

import asyncio

import pytest

from data_models.patient import PatientResponse
from data_models.problem_details_exceptions import BadRequestException, NotFoundException
from services.patient_service import PatientService


def _run(coro):
    return asyncio.run(coro)


class _FakeApiQueryService:
    def __init__(self, patient: PatientResponse | None):
        self.patient = patient
        self.last_phone: str | None = None

    async def query_patient_by_phone(self, phone_number: str):
        self.last_phone = phone_number
        return self.patient


def test_get_patient_by_phone_normalizes_and_returns_patient():
    expected = PatientResponse(
        patient_id="P001",
        first_name="John",
        last_name="Smith",
        phone="+15551234567",
        date_of_birth="1985-03-15",
        has_active_insurance=True,
        last_visit_date="2024-12-15",
    )
    fake = _FakeApiQueryService(expected)
    service = PatientService(api_query_service=fake)

    result = _run(service.get_patient_by_phone("(555) 123-4567"))

    assert fake.last_phone == "5551234567"
    assert result.patient_id == "P001"


def test_get_patient_by_phone_raises_not_found_when_missing():
    fake = _FakeApiQueryService(None)
    service = PatientService(api_query_service=fake)

    with pytest.raises(NotFoundException):
        _run(service.get_patient_by_phone("5551234567"))


def test_get_patient_by_phone_rejects_invalid_format():
    fake = _FakeApiQueryService(None)
    service = PatientService(api_query_service=fake)

    with pytest.raises(BadRequestException):
        _run(service.get_patient_by_phone("abc"))
