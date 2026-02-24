"""
Required Test Cases for the REST API Wrapper
These tests must pass for the assessment to be considered complete.

You are given ONE known patient phone number to start: 5551234567
There are other patients in the system — find them through exploration.

Run with: pytest test_requirements.py -v
"""

import pytest
import requests
import time
import random
from datetime import datetime, timedelta

# Your API should be running on port 3000
BASE_URL = "http://localhost:3000/api/v1"


def _next_weekday(start=None, min_days_ahead=1):
    """Return the next Monday-Friday date string (YYYY-MM-DD)."""
    start = start or datetime.now()
    candidate = start + timedelta(days=min_days_ahead)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.strftime('%Y-%m-%d')


def _next_weekend():
    """Return the next Saturday date string (YYYY-MM-DD)."""
    today = datetime.now()
    days_ahead = 5 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')


# ---------------------------------------------------------------------------
# Patient Lookup
# ---------------------------------------------------------------------------
class TestPatientLookup:

    def test_patient_found(self):
        """Should return patient data for a known phone number"""
        response = requests.get(f"{BASE_URL}/patients/5551234567")
        assert response.status_code == 200

        data = response.json()
        required_fields = [
            'patient_id', 'first_name', 'last_name',
            'phone', 'date_of_birth', 'has_active_insurance', 'last_visit_date'
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_patient_not_found(self):
        """Should return 404 for a phone number with no patient"""
        response = requests.get(f"{BASE_URL}/patients/9999999999")
        assert response.status_code == 404

    def test_phone_format_handling(self):
        """Same patient should be found regardless of phone format"""
        formats = ['5551234567', '(555) 123-4567', '555-123-4567', '+15551234567']
        ids = set()
        for fmt in formats:
            response = requests.get(f"{BASE_URL}/patients/{fmt}")
            assert response.status_code == 200, f"Failed for format: {fmt}"
            ids.add(response.json()['patient_id'])

        assert len(ids) == 1, "All formats should resolve to the same patient"

    def test_dates_are_normalized(self):
        """All date fields should be YYYY-MM-DD"""
        response = requests.get(f"{BASE_URL}/patients/5551234567")
        data = response.json()

        for field in ['date_of_birth', 'last_visit_date']:
            value = data.get(field)
            if value is not None:
                assert len(value) == 10 and value[4] == '-' and value[7] == '-', \
                    f"{field} should be YYYY-MM-DD, got: {value}"
                datetime.strptime(value, '%Y-%m-%d')

    def test_booleans_are_booleans(self):
        """Insurance status should be a real boolean, not a string"""
        response = requests.get(f"{BASE_URL}/patients/5551234567")
        data = response.json()

        assert isinstance(data['has_active_insurance'], bool), \
            f"Expected bool, got {type(data['has_active_insurance'])}"

    def test_response_time(self):
        """Must respond in under 2 seconds (warm cache is acceptable)"""
        # Warm request
        requests.get(f"{BASE_URL}/patients/5551234567")

        start = time.time()
        response = requests.get(f"{BASE_URL}/patients/5551234567")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0, f"Response took {elapsed:.2f}s, must be under 2s"


# ---------------------------------------------------------------------------
# Appointment Availability
# ---------------------------------------------------------------------------
class TestAppointmentAvailability:

    def test_weekday_returns_slots(self):
        """A weekday should have available slots"""
        weekday = _next_weekday()
        response = requests.get(
            f"{BASE_URL}/appointments/availability",
            params={'date': weekday}
        )
        assert response.status_code == 200

        data = response.json()
        assert 'available_slots' in data
        assert len(data['available_slots']) > 0

    def test_weekend_returns_empty(self):
        """Weekends should return no available slots"""
        saturday = _next_weekend()
        response = requests.get(
            f"{BASE_URL}/appointments/availability",
            params={'date': saturday}
        )
        assert response.status_code == 200
        assert len(response.json()['available_slots']) == 0

    def test_no_lunch_slots(self):
        """No slots should be offered between 12:00-12:59"""
        weekday = _next_weekday()
        response = requests.get(
            f"{BASE_URL}/appointments/availability",
            params={'date': weekday}
        )
        slots = response.json()['available_slots']
        for slot in slots:
            hour = int(slot['time'].split(':')[0])
            assert hour != 12, f"Slot at {slot['time']} falls during lunch break"

    def test_slot_has_required_fields(self):
        """Each slot should include time, dentist_id, and dentist_name"""
        weekday = _next_weekday()
        response = requests.get(
            f"{BASE_URL}/appointments/availability",
            params={'date': weekday}
        )
        slots = response.json()['available_slots']
        for slot in slots:
            assert 'time' in slot
            assert 'dentist_id' in slot
            assert 'dentist_name' in slot

    def test_filter_by_dentist(self):
        """When filtered by dentist, all returned slots should be for that dentist"""
        weekday = _next_weekday()
        response = requests.get(
            f"{BASE_URL}/appointments/availability",
            params={'date': weekday, 'dentist_id': 'D001'}
        )
        assert response.status_code == 200

        slots = response.json()['available_slots']
        for slot in slots:
            assert slot['dentist_id'] == 'D001'

    def test_missing_date_returns_400(self):
        """Omitting the required date parameter should return 400"""
        response = requests.get(f"{BASE_URL}/appointments/availability")
        assert response.status_code == 400

    def test_booked_slot_excluded_from_availability(self):
        """A known booked slot should not appear in availability results"""
        response = requests.get(
            f"{BASE_URL}/appointments/availability",
            params={'date': '2027-06-15', 'dentist_id': 'D001'}
        )
        assert response.status_code == 200

        slots = response.json()['available_slots']
        booked_times = [s['time'] for s in slots if s['time'] == '10:00']
        assert len(booked_times) == 0, \
            "10:00 on 2027-06-15 for D001 is already booked and should not appear"


# ---------------------------------------------------------------------------
# Appointment Booking
# ---------------------------------------------------------------------------
class TestAppointmentBooking:

    def test_successful_booking(self):
        """Should book an available slot and return confirmation"""
        future_weekday = _next_weekday(min_days_ahead=random.randint(30, 365))

        response = requests.post(f"{BASE_URL}/appointments/book", json={
            "patient_id": "P001",
            "dentist_id": "D001",
            "appointment_date": future_weekday,
            "appointment_time": "14:00",
            "reason": "Regular checkup"
        })
        assert response.status_code in [200, 201]

        data = response.json()
        assert 'appointment_id' in data
        assert 'confirmation_number' in data
        assert data['status'] == 'confirmed'

    def test_nonexistent_patient_returns_404(self):
        """Booking for a patient that doesn't exist should fail"""
        weekday = _next_weekday()

        response = requests.post(f"{BASE_URL}/appointments/book", json={
            "patient_id": "P999",
            "dentist_id": "D001",
            "appointment_date": weekday,
            "appointment_time": "15:00",
            "reason": "Checkup"
        })
        assert response.status_code == 404

    def test_seeded_conflict_returns_409(self):
        """Booking an already-occupied slot should return 409.
        The slot 2027-06-15 at 10:00 with D001 is pre-booked in the legacy system."""
        response = requests.post(f"{BASE_URL}/appointments/book", json={
            "patient_id": "P002",
            "dentist_id": "D001",
            "appointment_date": "2027-06-15",
            "appointment_time": "10:00",
            "reason": "Conflict test"
        })
        assert response.status_code == 409

    def test_idempotent_booking(self):
        """Submitting the same booking twice should not create a duplicate.
        Second request should return the same confirmation, not an error."""
        idempotent_date = _next_weekday(min_days_ahead=500)

        booking = {
            "patient_id": "P001",
            "dentist_id": "D002",
            "appointment_date": idempotent_date,
            "appointment_time": "15:30",
            "reason": "Idempotency test"
        }

        first = requests.post(f"{BASE_URL}/appointments/book", json=booking)
        assert first.status_code in [200, 201]

        first_data = first.json()
        assert first_data['status'] == 'confirmed'

        # Same exact request again
        second = requests.post(f"{BASE_URL}/appointments/book", json=booking)
        assert second.status_code in [200, 201], \
            f"Duplicate booking should succeed (idempotent), got {second.status_code}"

        second_data = second.json()
        assert second_data['status'] == 'confirmed'
        assert second_data['confirmation_number'] == first_data['confirmation_number'], \
            "Duplicate booking should return the same confirmation number"

    def test_malformed_request_returns_400(self):
        """Sending incomplete or empty booking data should return 400"""
        response = requests.post(f"{BASE_URL}/appointments/book", json={})
        assert response.status_code == 400

        response = requests.post(f"{BASE_URL}/appointments/book", json={
            "patient_id": "P001"
        })
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Error Handling & Resilience
# ---------------------------------------------------------------------------
class TestResilience:

    def test_api_stays_up_under_legacy_failures(self):
        """Legacy API fails randomly — your wrapper should handle it gracefully"""
        results = []
        for _ in range(10):
            r = requests.get(f"{BASE_URL}/patients/5551234567")
            results.append(r.status_code)

        successes = results.count(200)
        assert successes > 0, "Should handle at least some requests successfully"

        for code in results:
            assert code in [200, 503, 504], f"Unexpected status code: {code}"

    def test_errors_are_json(self):
        """Error responses should be JSON, never HTML"""
        response = requests.get(f"{BASE_URL}/patients/9999999999")
        assert response.headers['Content-Type'].startswith('application/json')


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
