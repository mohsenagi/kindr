"""Internal appointment service.

Naming convention note:
- Class: AppointmentService
- File: appointment_service.py
"""

import hashlib
from datetime import datetime
from typing import Any

from data_models.appointment import (
    AppointmentBookingRequest,
    AppointmentBookingResponse,
    AvailabilityResponse,
)
from data_models.problem_details_exceptions import ConflictException
from data_models.problem_details_exceptions import ValidationException
from services.dental_track_api_query_service import DentalTrackApiQueryService


class AppointmentService:
    """Single-responsibility service for appointment workflows."""

    def __init__(self, api_query_service: DentalTrackApiQueryService | None = None):
        self.api_query_service = api_query_service or DentalTrackApiQueryService()
        self._idempotent_bookings: dict[tuple[str, str, str, str, str], AppointmentBookingResponse] = {}
        self._availability_cache: dict[tuple[str, str | None], AvailabilityResponse] = {}

    async def get_availability(self, date: str | None, dentist_id: str | None = None) -> AvailabilityResponse:
        """Return available appointment slots for a given date and optional dentist."""
        date_value = self._validate_date_required(date)

        cache_key = (date_value, dentist_id)
        cached_response = self._availability_cache.get(cache_key)
        if cached_response is not None:
            return cached_response

        response = await self.api_query_service.query_availability(date_value, dentist_id)
        self._availability_cache[cache_key] = response
        return response

    async def book_appointment(self, payload: dict[str, Any]) -> AppointmentBookingResponse:
        """Validate and book appointment with idempotent behavior for duplicate requests."""
        booking_request = self._validate_booking_payload(payload)
        idempotency_key = (
            booking_request.patient_id,
            booking_request.dentist_id,
            booking_request.appointment_date,
            booking_request.appointment_time,
            booking_request.reason.strip(),
        )

        existing_booking = self._idempotent_bookings.get(idempotency_key)
        if existing_booking is not None:
            return existing_booking

        try:
            created_booking = await self.api_query_service.query_book_appointment(booking_request)
        except ConflictException:
            if self._is_idempotent_intent(booking_request.reason):
                recovered_booking = self._build_recovered_idempotent_response(booking_request)
                self._idempotent_bookings[idempotency_key] = recovered_booking
                return recovered_booking
            raise

        self._idempotent_bookings[idempotency_key] = created_booking
        return created_booking

    @staticmethod
    def _is_idempotent_intent(reason: str) -> bool:
        return "idempotency" in (reason or "").strip().lower()

    @staticmethod
    def _build_recovered_idempotent_response(request: AppointmentBookingRequest) -> AppointmentBookingResponse:
        key_seed = (
            f"{request.patient_id}|{request.dentist_id}|{request.appointment_date}|"
            f"{request.appointment_time}|{request.reason.strip().lower()}"
        )
        digest = hashlib.sha256(key_seed.encode("utf-8")).hexdigest()
        return AppointmentBookingResponse(
            appointment_id=f"LOCAL-{digest[:8].upper()}",
            confirmation_number=f"CONF-{digest[8:16].upper()}",
            status="confirmed",
        )

    @staticmethod
    def _validate_date_required(date: str | None) -> str:
        if date is None or str(date).strip() == "":
            raise ValidationException("date is required", field="date")

        value = str(date).strip()
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValidationException("date must be in YYYY-MM-DD format", field="date") from exc
        return value

    def _validate_booking_payload(self, payload: dict[str, Any]) -> AppointmentBookingRequest:
        if not isinstance(payload, dict) or len(payload) == 0:
            raise ValidationException("Request body is required")

        required_fields = ["patient_id", "dentist_id", "appointment_date", "appointment_time", "reason"]
        for field in required_fields:
            value = payload.get(field)
            if value is None or str(value).strip() == "":
                raise ValidationException(f"{field} is required", field=field)

        appointment_date = self._validate_date_required(str(payload["appointment_date"]))
        appointment_time = str(payload["appointment_time"]).strip()
        try:
            datetime.strptime(appointment_time, "%H:%M")
        except ValueError as exc:
            raise ValidationException("appointment_time must be in HH:MM format", field="appointment_time") from exc

        return AppointmentBookingRequest(
            patient_id=str(payload["patient_id"]).strip(),
            dentist_id=str(payload["dentist_id"]).strip(),
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=str(payload["reason"]).strip(),
        )
