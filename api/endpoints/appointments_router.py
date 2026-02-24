"""Appointment endpoints module."""

from fastapi import APIRouter

from data_models.appointment import AppointmentBookingRequest
from data_models.problem_details_exceptions import NotImplementedApiException


appointments_router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


@appointments_router.get("/availability")
async def get_availability(date: str, dentist_id: str | None = None):
    """Get appointment availability."""
    raise NotImplementedApiException(
        detail=f"Availability lookup not implemented yet for date={date}, dentist_id={dentist_id}"
    )


@appointments_router.post("/book")
async def book_appointment(payload: AppointmentBookingRequest):
    """Book an appointment."""
    raise NotImplementedApiException(detail=f"Booking not implemented yet for patient {payload.patient_id}")
