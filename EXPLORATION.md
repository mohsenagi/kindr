# Legacy API Exploration Notes (DentalTrack Pro)

Base URL explored: `https://takehome-production.up.railway.app/`
Date: 2026-02-24

## High-level findings

- API advertises SOAP-like services, but requests/responses are JSON with SOAP-style envelope keys.
- `GET /soap/*` endpoints are mostly not allowed (`405`); service operations are `POST`.
- Legacy service is unstable and intermittently returns `500` (`{"error": "Database connection timeout"}`).
- Field naming is inconsistent:
  - Patient request expects `phoneNumber` (camelCase), not `phone`.
  - Booking expects camelCase fields (`patientId`, `dentistId`, `appointmentDate`, `appointmentTime`).
  - Availability slot fields are mixed case (`DentistName`, `dentistID`, `timeSlot`).
- Availability endpoint appears to ignore dentist filter in the request (returns all dentists), so wrapper should filter.
- Booking is **not idempotent** in legacy API:
  - First call can succeed (`201`), second identical call returns `409 conflict`.

---

## Raw terminal exploration excerpts

### 1) Discover base endpoints

Command:

```powershell
GET https://takehome-production.up.railway.app/
```

Output excerpt:

```text
Status: 200
{
  "endpoints": [
    "/health - Health check",
    "/soap/PatientService - Get patient information",
    "/soap/AppointmentService/GetAvailability - Get available slots",
    "/soap/AppointmentService/BookAppointment - Book an appointment"
  ],
  "note": "This is a legacy system simulator with intentional delays and quirks",
  "service": "DentalTrack Pro SOAP API Simulator",
  "status": "operational",
  "version": "2.1"
}
```

### 2) Health check

Command:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "https://takehome-production.up.railway.app/health" -Method GET
```

Output excerpt:

```text
Status: 200
{
  "status": "operational",
  "system": "DentalTrack Pro v2.1"
}
```

### 3) Confirm methods on service routes

Command:

```powershell
curl.exe -s -i https://takehome-production.up.railway.app/soap/PatientService
```

Output excerpt:

```text
HTTP/1.1 405 Method Not Allowed
Allow: POST, OPTIONS
Content-Type: text/html; charset=utf-8
```

### 4) Patient lookup payload key discovery

Command:

```powershell
# brute-force request keys (status only)
phone => 400
phone_number => 400
phoneNumber => 200
Phone => 400
PhoneNumber => 400
patient_phone => 400
telephone => 400
mobile => 400
```

Conclusion: accepted key is `phoneNumber`.

### 5) Patient lookup success response

Command:

```powershell
curl.exe -s -i -X POST https://takehome-production.up.railway.app/soap/PatientService -H "Content-Type: application/json" --data-binary "@tmp_patient.json"
# tmp_patient.json => {"phoneNumber":"5551234567"}
```

Output excerpt:

```text
HTTP/1.1 200 OK
{
  "soap:Envelope": {
    "soap:Body": {
      "GetPatientResponse": {
        "Patient": {
          "dob": "03/15/1985",
          "firstName": "John",
          "insuranceActive": "Y",
          "lastName": "Smith",
          "lastVisit": "2024-12-15",
          "patientId": "P001",
          "phoneNumber": "(555) 123-4567"
        }
      }
    }
  }
}
```

### 6) Patient not found and transient errors

Unknown patient command payload: `{"phoneNumber":"9999999999"}`

Output excerpt:

```text
HTTP/1.1 404 Not Found
{
  "soap:Envelope": {
    "soap:Body": {
      "PatientNotFound": {
        "message": "No patient record found"
      }
    }
  }
}
```

Also observed intermittently:

```text
HTTP/1.1 500 Internal Server Error
{
  "error": "Database connection timeout"
}
```

### 7) Availability request/response

Command:

```powershell
curl.exe -s -i -X POST https://takehome-production.up.railway.app/soap/AppointmentService/GetAvailability -H "Content-Type: application/json" --data-binary "@availability_payload.json"
# availability_payload.json => {"date":"2027-06-15","dentist_id":"D001"}
```

Output excerpt:

```text
HTTP/1.1 200 OK
{
  "soap:Envelope": {
    "soap:Body": {
      "GetAvailabilityResponse": {
        "Date": "2027-06-15",
        "Slots": [
          {"DentistName":"Dr. Williams","dentistID":"D001","timeSlot":"09:00"},
          {"DentistName":"Dr. Patel","dentistID":"D002","timeSlot":"09:00"},
          ...
        ]
      }
    }
  }
}
```

Weekend behavior (`{"date":"2026-02-28"}`):

```text
HTTP/1.1 200 OK
{"soap:Envelope":{"soap:Body":{"GetAvailabilityResponse":{"Slots":[]}}}}
```

Missing date (`{}`):

```text
HTTP/1.1 400 Bad Request
{"error":"Invalid date format"}
```

### 8) Booking request format + conflict behavior

Payload key discovery (status only):

```text
template_1 snake_case => 400
template_2 camelCase with reason => 409
template_3 camelCase with reasonForVisit => 409
template_4 PascalCase => 400
template_5 mixed ID casing => 400
```

Command (success sample):

```powershell
# {"patientId":"P001","dentistId":"D001","appointmentDate":"2027-08-12","appointmentTime":"14:00","reason":"Regular checkup"}
curl.exe -s -i -X POST https://takehome-production.up.railway.app/soap/AppointmentService/BookAppointment -H "Content-Type: application/json" --data-binary "@tmp_booking_success.json"
```

Output excerpt:

```text
HTTP/1.1 201 Created
{
  "soap:Envelope": {
    "soap:Body": {
      "BookAppointmentResponse": {
        "ConfirmationNum": "CONF20791",
        "Status": "confirmed",
        "appointmentID": "A055"
      }
    }
  }
}
```

Known conflict sample (`2027-06-15`, `10:00`, `D001`):

```text
HTTP/1.1 409 Conflict
{
  "soap:Envelope": {
    "soap:Body": {
      "BookAppointmentResponse": {
        "message": "Time slot no longer available",
        "status": "conflict"
      }
    }
  }
}
```

Duplicate booking behavior observed:

```text
First call  -> HTTP/1.1 201 Created
Second call -> HTTP/1.1 409 Conflict
```

---

## Implementation implications for wrapper

- Use upstream `POST` for all business operations.
- Map wrapper inputs to legacy camelCase contract.
- Normalize legacy response structure from SOAP-like envelope to simple REST JSON.
- Add retry + timeout + graceful error mapping for random upstream `500`s.
- Implement idempotency in wrapper layer (legacy API is not idempotent).
- Filter availability by dentist in wrapper (upstream may return unfiltered slots).
