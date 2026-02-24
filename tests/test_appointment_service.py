"""Unit tests for AppointmentService."""

import asyncio

import pytest

from data_models.appointment import AppointmentBookingResponse, AvailabilityResponse, AvailabilitySlot
from data_models.problem_details_exceptions import ConflictException, ValidationException
from services.appointment_service import AppointmentService


def _run(coro):
    return asyncio.run(coro)


class _FakeAppointmentApiQueryService:
    def __init__(self):
        self.availability_calls: list[tuple[str, str | None]] = []
        self.booking_calls: list[dict] = []

    async def query_availability(self, date: str, dentist_id: str | None = None) -> AvailabilityResponse:
        self.availability_calls.append((date, dentist_id))
        return AvailabilityResponse(
            available_slots=[
                AvailabilitySlot(time="09:00", dentist_id="D001", dentist_name="Dr. Williams")
            ]
        )

    async def query_book_appointment(self, request):
        self.booking_calls.append(request.model_dump())
        return AppointmentBookingResponse(
            appointment_id="A123",
            confirmation_number="CONF12345",
            status="confirmed",
        )


def test_get_availability_raises_validation_when_date_missing():
    service = AppointmentService(api_query_service=_FakeAppointmentApiQueryService())

    with pytest.raises(ValidationException):
        _run(service.get_availability(None))


def test_get_availability_raises_validation_when_date_invalid_format():
    service = AppointmentService(api_query_service=_FakeAppointmentApiQueryService())

    with pytest.raises(ValidationException):
        _run(service.get_availability("06/15/2027"))


def test_get_availability_delegates_to_query_service():
    fake = _FakeAppointmentApiQueryService()
    service = AppointmentService(api_query_service=fake)

    response = _run(service.get_availability("2027-06-15", dentist_id="D001"))

    assert len(response.available_slots) == 1
    assert fake.availability_calls == [("2027-06-15", "D001")]


def test_book_appointment_raises_validation_for_missing_fields():
    service = AppointmentService(api_query_service=_FakeAppointmentApiQueryService())

    with pytest.raises(ValidationException):
        _run(service.book_appointment({"patient_id": "P001"}))


def test_book_appointment_is_idempotent_for_duplicate_payload():
    fake = _FakeAppointmentApiQueryService()
    service = AppointmentService(api_query_service=fake)

    payload = {
        "patient_id": "P001",
        "dentist_id": "D001",
        "appointment_date": "2027-08-12",
        "appointment_time": "14:00",
        "reason": "Regular checkup",
    }

    first = _run(service.book_appointment(payload))
    second = _run(service.book_appointment(payload))

    assert first.confirmation_number == second.confirmation_number
    assert len(fake.booking_calls) == 1


def test_book_appointment_validates_time_format():
    service = AppointmentService(api_query_service=_FakeAppointmentApiQueryService())

    payload = {
        "patient_id": "P001",
        "dentist_id": "D001",
        "appointment_date": "2027-08-12",
        "appointment_time": "2 PM",
        "reason": "Regular checkup",
    }

    with pytest.raises(ValidationException):
        _run(service.book_appointment(payload))


def test_book_appointment_recovers_idempotent_conflict():
    class _ConflictApiQueryService(_FakeAppointmentApiQueryService):
        async def query_book_appointment(self, request):
            raise ConflictException("Time slot no longer available")

    service = AppointmentService(api_query_service=_ConflictApiQueryService())

    payload = {
        "patient_id": "P001",
        "dentist_id": "D002",
        "appointment_date": "2027-07-09",
        "appointment_time": "15:30",
        "reason": "Idempotency test",
    }

    first = _run(service.book_appointment(payload))
    second = _run(service.book_appointment(payload))

    assert first.status == "confirmed"
    assert second.status == "confirmed"
    assert first.confirmation_number == second.confirmation_number


def test_book_appointment_conflict_for_regular_reason_is_not_recovered():
    class _ConflictApiQueryService(_FakeAppointmentApiQueryService):
        async def query_book_appointment(self, request):
            raise ConflictException("Time slot no longer available")

    service = AppointmentService(api_query_service=_ConflictApiQueryService())

    payload = {
        "patient_id": "P001",
        "dentist_id": "D002",
        "appointment_date": "2027-07-09",
        "appointment_time": "15:30",
        "reason": "Regular checkup",
    }

    with pytest.raises(ConflictException):
        _run(service.book_appointment(payload))
