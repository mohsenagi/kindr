"""Unit tests for DentalTrackApiQueryService."""

import asyncio

import pytest

from data_models.appointment import AppointmentBookingRequest
from data_models.problem_details_exceptions import ConflictException
from services.dental_track_api_query_service import DentalTrackApiQueryService


def _run(coro):
    return asyncio.run(coro)


def test_query_patient_by_phone_normalizes_fields(monkeypatch):
    service = DentalTrackApiQueryService()

    async def fake_post_json(path, payload, **kwargs):
        assert path == "/soap/PatientService"
        assert payload["phoneNumber"] == "5551234567"
        return {
            "soap:Envelope": {
                "soap:Body": {
                    "GetPatientResponse": {
                        "Patient": {
                            "patientId": "P001",
                            "firstName": "John",
                            "lastName": "Smith",
                            "phoneNumber": "(555) 123-4567",
                            "dob": "03/15/1985",
                            "insuranceActive": "Y",
                            "lastVisit": "2024-12-15",
                        }
                    }
                }
            }
        }

    monkeypatch.setattr(service, "_post_json", fake_post_json)

    patient = _run(service.query_patient_by_phone("(555) 123-4567"))

    assert patient is not None
    assert patient.patient_id == "P001"
    assert patient.phone == "+15551234567"
    assert patient.date_of_birth == "1985-03-15"
    assert patient.has_active_insurance is True
    assert patient.last_visit_date == "2024-12-15"


def test_query_patient_by_phone_returns_none_when_not_found(monkeypatch):
    service = DentalTrackApiQueryService()

    async def fake_post_json(path, payload, **kwargs):
        return {
            "soap:Envelope": {
                "soap:Body": {
                    "PatientNotFound": {"message": "No patient record found"}
                }
            }
        }

    monkeypatch.setattr(service, "_post_json", fake_post_json)

    patient = _run(service.query_patient_by_phone("9999999999"))

    assert patient is None


def test_query_availability_filters_lunch_and_dentist(monkeypatch):
    service = DentalTrackApiQueryService()

    async def fake_post_json(path, payload, **kwargs):
        assert path == "/soap/AppointmentService/GetAvailability"
        assert payload["date"] == "2027-06-15"
        return {
            "soap:Envelope": {
                "soap:Body": {
                    "GetAvailabilityResponse": {
                        "Slots": [
                            {"DentistName": "Dr. Williams", "dentistID": "D001", "timeSlot": "11:30"},
                            {"DentistName": "Dr. Williams", "dentistID": "D001", "timeSlot": "12:00"},
                            {"DentistName": "Dr. Patel", "dentistID": "D002", "timeSlot": "13:00"},
                        ]
                    }
                }
            }
        }

    monkeypatch.setattr(service, "_post_json", fake_post_json)

    result = _run(service.query_availability("2027-06-15", dentist_id="D001"))

    assert len(result.available_slots) == 1
    assert result.available_slots[0].time == "11:30"
    assert result.available_slots[0].dentist_id == "D001"


def test_query_book_appointment_maps_success(monkeypatch):
    service = DentalTrackApiQueryService()

    async def fake_post_json(path, payload, **kwargs):
        assert path == "/soap/AppointmentService/BookAppointment"
        assert payload["patientId"] == "P001"
        return {
            "soap:Envelope": {
                "soap:Body": {
                    "BookAppointmentResponse": {
                        "appointmentID": "A055",
                        "ConfirmationNum": "CONF20791",
                        "Status": "confirmed",
                    }
                }
            }
        }

    monkeypatch.setattr(service, "_post_json", fake_post_json)

    request = AppointmentBookingRequest(
        patient_id="P001",
        dentist_id="D001",
        appointment_date="2027-08-12",
        appointment_time="14:00",
        reason="Regular checkup",
    )

    booking = _run(service.query_book_appointment(request))

    assert booking.appointment_id == "A055"
    assert booking.confirmation_number == "CONF20791"
    assert booking.status == "confirmed"


def test_query_book_appointment_conflict_raises(monkeypatch):
    service = DentalTrackApiQueryService()

    async def fake_post_json(path, payload, **kwargs):
        return {
            "soap:Envelope": {
                "soap:Body": {
                    "BookAppointmentResponse": {
                        "status": "conflict",
                        "message": "Time slot no longer available",
                    }
                }
            }
        }

    monkeypatch.setattr(service, "_post_json", fake_post_json)

    request = AppointmentBookingRequest(
        patient_id="P001",
        dentist_id="D001",
        appointment_date="2027-08-12",
        appointment_time="14:00",
        reason="Regular checkup",
    )

    with pytest.raises(ConflictException):
        _run(service.query_book_appointment(request))
