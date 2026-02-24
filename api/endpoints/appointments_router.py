"""Appointment endpoints module."""

from typing import Any

from fastapi import APIRouter, Body

from data_models.appointment import AppointmentBookingResponse, AvailabilityResponse
from services.appointment_service import AppointmentService


appointments_router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])
appointment_service = AppointmentService()


@appointments_router.get("/availability")
async def get_availability(date: str | None = None, dentist_id: str | None = None) -> AvailabilityResponse:
    """Get appointment availability."""
    return await appointment_service.get_availability(date=date, dentist_id=dentist_id)


@appointments_router.post("/book")
async def book_appointment(payload: dict[str, Any] = Body(...)) -> AppointmentBookingResponse:
    """Book an appointment."""
    return await appointment_service.book_appointment(payload)
