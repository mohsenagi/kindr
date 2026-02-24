"""DentalTrack legacy API query adapter.

Naming convention note:
- In this Python codebase, file names mirror class names in snake_case.
- Class: DentalTrackApiQueryService
- File: dental_track_api_query_service.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from data_models.appointment import (
    AppointmentBookingRequest,
    AppointmentBookingResponse,
    AvailabilityResponse,
    AvailabilitySlot,
)
from data_models.patient import PatientResponse
from data_models.problem_details_exceptions import (
    BadRequestException,
    ConflictException,
    GatewayTimeoutException,
    NotFoundException,
    ServiceUnavailableException,
)


class DentalTrackApiQueryService:
    """Adapter over DentalTrack Pro legacy endpoints.

    This class intentionally hides SOAP-like envelopes, inconsistent casing,
    and transient failure behavior, so higher-level services can work against
    stable, canonical models.
    """

    def __init__(
        self,
        base_url: str = "https://takehome-production.up.railway.app",
        timeout_seconds: float = 0.9,
        max_attempts: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

    async def query_patient_by_phone(self, phone_number: str) -> PatientResponse | None:
        """Lookup patient by phone number and return canonical patient model.

        Returns `None` if patient does not exist.
        """
        payload = {"phoneNumber": self._normalize_phone_for_legacy(phone_number)}
        response_json = await self._post_json(
            "/soap/PatientService",
            payload,
            timeout_seconds=0.9,
            max_attempts=3,
        )

        body = self._soap_body(response_json)
        patient_not_found = body.get("PatientNotFound")
        if patient_not_found:
            return None

        patient = body.get("GetPatientResponse", {}).get("Patient")
        if not isinstance(patient, dict):
            raise ServiceUnavailableException("Legacy patient payload format is invalid")

        return PatientResponse(
            patient_id=str(patient.get("patientId", "")),
            first_name=str(patient.get("firstName", "")),
            last_name=str(patient.get("lastName", "")),
            phone=self._normalize_phone_canonical(str(patient.get("phoneNumber", ""))),
            date_of_birth=self._normalize_date(str(patient.get("dob", ""))),
            has_active_insurance=self._normalize_insurance(patient.get("insuranceActive")),
            last_visit_date=self._normalize_date(str(patient.get("lastVisit", ""))),
        )

    async def query_availability(self, date: str, dentist_id: str | None = None) -> AvailabilityResponse:
        """Get canonical availability slots for a date and optional dentist."""
        payload: dict[str, Any] = {"date": date}
        if dentist_id:
            payload["dentist_id"] = dentist_id

        response_json = await self._post_json(
            "/soap/AppointmentService/GetAvailability",
            payload,
            timeout_seconds=2.5,
            max_attempts=4,
        )
        body = self._soap_body(response_json)
        raw_slots = body.get("GetAvailabilityResponse", {}).get("Slots", [])

        slots: list[AvailabilitySlot] = []
        if isinstance(raw_slots, list):
            for raw in raw_slots:
                if not isinstance(raw, dict):
                    continue
                raw_time = str(raw.get("timeSlot", ""))
                hour = self._hour_from_time(raw_time)
                if hour == 12:
                    continue

                slot = AvailabilitySlot(
                    time=raw_time,
                    dentist_id=str(raw.get("dentistID", "")),
                    dentist_name=str(raw.get("DentistName", "")),
                )
                if dentist_id and slot.dentist_id != dentist_id:
                    continue
                slots.append(slot)

        return AvailabilityResponse(available_slots=slots)

    async def query_book_appointment(
        self, request: AppointmentBookingRequest
    ) -> AppointmentBookingResponse:
        """Book an appointment and return canonical booking response."""
        payload = {
            "patientId": request.patient_id,
            "dentistId": request.dentist_id,
            "appointmentDate": request.appointment_date,
            "appointmentTime": request.appointment_time,
            "reason": request.reason,
        }

        response_json = await self._post_json(
            "/soap/AppointmentService/BookAppointment",
            payload,
            timeout_seconds=2.5,
            max_attempts=4,
        )
        body = self._soap_body(response_json)
        booking_response = body.get("BookAppointmentResponse", {})

        status_value = str(booking_response.get("Status") or booking_response.get("status") or "").lower()
        if status_value == "conflict":
            raise ConflictException(str(booking_response.get("message", "Time slot no longer available")))

        appointment_id = booking_response.get("appointmentID")
        confirmation = booking_response.get("ConfirmationNum")
        status_text = booking_response.get("Status")
        if not appointment_id or not confirmation or not status_text:
            raise ServiceUnavailableException("Legacy booking payload format is invalid")

        return AppointmentBookingResponse(
            appointment_id=str(appointment_id),
            confirmation_number=str(confirmation),
            status=str(status_text).lower(),
        )

    async def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        timeout_seconds: float | None = None,
        max_attempts: int | None = None,
    ) -> dict[str, Any]:
        """POST JSON to legacy endpoint with retry and deterministic error mapping."""
        url = f"{self.base_url}{path}"
        last_exception: Exception | None = None
        timeout_value = timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        attempts = max_attempts if max_attempts is not None else self.max_attempts

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_value) as client:
                    response = await client.post(url, json=payload)
            except httpx.TimeoutException as exc:
                last_exception = exc
                if attempt == attempts:
                    raise GatewayTimeoutException("Legacy API request timed out") from exc
                continue
            except httpx.HTTPError as exc:
                last_exception = exc
                if attempt == attempts:
                    raise ServiceUnavailableException("Legacy API connection failed") from exc
                continue

            if response.status_code in (500, 502, 503, 504):
                if attempt == attempts:
                    raise ServiceUnavailableException("Legacy API is temporarily unavailable")
                continue

            parsed = self._safe_json(response)

            if response.status_code == 404:
                if isinstance(parsed, dict) and parsed.get("error") == "Patient not found":
                    raise NotFoundException("Patient not found")
                return parsed

            if response.status_code == 409:
                message = self._extract_conflict_message(parsed)
                raise ConflictException(message)

            if response.status_code == 400:
                fault = self._extract_fault_message(parsed) or self._extract_error_message(parsed) or "Invalid request"
                raise BadRequestException(fault)

            if response.status_code >= 500:
                raise ServiceUnavailableException("Legacy API is temporarily unavailable")

            if response.status_code not in (200, 201):
                raise ServiceUnavailableException(f"Unexpected legacy status code: {response.status_code}")

            return parsed

        if isinstance(last_exception, httpx.TimeoutException):
            raise GatewayTimeoutException("Legacy API request timed out") from last_exception
        raise ServiceUnavailableException("Legacy API is temporarily unavailable")

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            parsed = response.json()
        except ValueError as exc:
            raise ServiceUnavailableException("Legacy API returned non-JSON payload") from exc
        if not isinstance(parsed, dict):
            raise ServiceUnavailableException("Legacy API returned unexpected payload type")
        return parsed

    @staticmethod
    def _soap_body(payload: dict[str, Any]) -> dict[str, Any]:
        envelope = payload.get("soap:Envelope")
        if not isinstance(envelope, dict):
            return {}
        body = envelope.get("soap:Body")
        if not isinstance(body, dict):
            return {}
        return body

    @staticmethod
    def _extract_fault_message(payload: dict[str, Any]) -> str | None:
        body = DentalTrackApiQueryService._soap_body(payload)
        fault = body.get("soap:Fault")
        if isinstance(fault, dict):
            return str(fault.get("faultstring") or "") or None
        return None

    @staticmethod
    def _extract_conflict_message(payload: dict[str, Any]) -> str:
        body = DentalTrackApiQueryService._soap_body(payload)
        message = body.get("BookAppointmentResponse", {}).get("message")
        if message:
            return str(message)
        return "Time slot no longer available"

    @staticmethod
    def _extract_error_message(payload: dict[str, Any]) -> str | None:
        error = payload.get("error")
        return str(error) if error else None

    @staticmethod
    def _normalize_phone_for_legacy(phone_number: str) -> str:
        digits = "".join(ch for ch in phone_number if ch.isdigit())
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        return digits

    @staticmethod
    def _normalize_phone_canonical(phone_number: str) -> str:
        digits = "".join(ch for ch in phone_number if ch.isdigit())
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        return phone_number

    @staticmethod
    def _normalize_insurance(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        text = str(value).strip().lower()
        return text in {"y", "yes", "true", "1", "active"}

    @staticmethod
    def _normalize_date(raw_date: str) -> str | None:
        value = (raw_date or "").strip()
        if not value:
            return None

        for date_format in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(value, date_format).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    @staticmethod
    def _hour_from_time(raw_time: str) -> int | None:
        try:
            return int(raw_time.split(":")[0])
        except (ValueError, IndexError, AttributeError):
            return None
