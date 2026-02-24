"""Appointment API models."""

from pydantic import BaseModel


class AvailabilitySlot(BaseModel):
    """One available appointment slot."""

    time: str
    dentist_id: str
    dentist_name: str


class AvailabilityResponse(BaseModel):
    """Available slots payload."""

    available_slots: list[AvailabilitySlot]


class AppointmentBookingRequest(BaseModel):
    """Booking request payload."""

    patient_id: str
    dentist_id: str
    appointment_date: str
    appointment_time: str
    reason: str


class AppointmentBookingResponse(BaseModel):
    """Booking response payload."""

    appointment_id: str
    confirmation_number: str
    status: str
