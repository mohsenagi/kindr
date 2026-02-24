# ARCHITECTURE.md

## Purpose

This wrapper API sits between our voice AI runtime and legacy PMS systems. The goal is to provide a stable, fast, and predictable contract (`/api/v1/...`) even when upstream systems are slow, inconsistent, or partially unavailable.

This document explains the key design decisions made in Part 1 and why they were made.

---

## 1) Layered Modularity

### Decision
Use clear layers with strict responsibilities:

- `api/` = transport layer only (routing, request entrypoints, middleware wiring)
- `services/` = business workflow orchestration and validation
- `data_models/` = canonical request/response/error models
- `services/dental_track_api_query_service.py` = external PMS adapter boundary

### Why

- **Interchangeability**: We can swap PMS adapters without rewriting API routes or workflow services.
- **Testability**: Services can be unit-tested with fake adapters (done for `PatientService` and `AppointmentService`).
- **Maintainability**: Routing concerns and business logic do not bleed into each other.
- **Future growth**: Supports adding integrations (OpenDental, Dentrix connector) while keeping application API stable.

### Example in code

- Routers are thin: `api/endpoints/patients_router.py`, `api/endpoints/appointments_router.py`
- Business logic is in services: `services/patient_service.py`, `services/appointment_service.py`
- Legacy interaction is isolated in one adapter: `services/dental_track_api_query_service.py`

---

## 2) Global Exception Handling + Problem Details Exceptions

### Decision
Implement a single global exception middleware and application-specific exceptions derived from `ProblemDetailsException`.

- Middleware: `api/infrastructure/global_exception_handler.py`
- Exception model: `data_models/problem_details_exceptions.py`

### Why

- **Single try/catch boundary**: One centralized place handles all raised application exceptions.
- **Consistent API errors**: Every failure is JSON with predictable structure (`title`, `errors`, code/message).
- **Cleaner services**: Services raise intentful exceptions (`ValidationException`, `NotFoundException`, etc.) without building HTTP responses.
- **Safer production behavior**: Unknown exceptions are caught and normalized to internal server error payloads (no HTML leakage).

### Outcome

A request failure path is deterministic and standardized across all endpoints.

---

## 3) Single Responsibility Services

### Decision
Create focused service classes per domain use case:

- `PatientService`:
  - phone normalization/validation
  - patient lookup orchestration
- `AppointmentService`:
  - availability validation + retrieval
  - booking validation + idempotency behavior

### Why

- **Cohesion**: Each service owns one domain area.
- **Low coupling**: Services call adapter interfaces rather than endpoint internals.
- **Easier evolution**: Booking/idempotency logic can change without touching routing or adapter contracts.
- **Better tests**: Service tests exercise business rules directly, independent of HTTP transport.

---

## 4) Plug-in Design for Legacy Systems

### Decision
Treat `DentalTrackApiQueryService` as the current PMS adapter implementation behind stable internal service contracts.

### Why

- The voice/API contract should not depend on any one PMS’s data format quirks.
- Different tenants can use different PMS providers.
- Integrations can be selected by tenant plan/subscription/region/policy without changing core workflows.

### Current adapter responsibilities

`DentalTrackApiQueryService` performs:

- request shape translation (our canonical -> legacy payload)
- response shape translation (SOAP-like envelope -> canonical models)
- normalization (dates, booleans, phone format)
- resilience behavior (timeouts, retries, status mapping)

### How this extends

We can introduce additional adapter implementations (e.g., `OpenDentalApiQueryService`, `DentrixLocalAgentQueryService`) that expose the same internal query methods used by services:

- `query_patient_by_phone(...)`
- `query_availability(...)`
- `query_book_appointment(...)`

At runtime, an adapter resolver can choose implementation by tenant metadata (PMS type, subscription tier, feature flags).

---

## 5) Performance and Reliability Trade-offs (Wrapper Context)

### Decision
Use bounded retries/timeouts at adapter layer and selective in-memory caching in services.

### Why

- Legacy API is intentionally unstable and slow.
- Voice-call experience requires fast responses and graceful failure handling.
- Tests assert strict latency behavior for patient lookup.

### Trade-offs accepted

- In-memory cache improves response time but is process-local (not shared across instances).
- Retry windows improve success rate but may increase tail latency if upstream remains unhealthy.
- For this assessment, this balance favors deterministic behavior under test and realistic resiliency.

---

## 6) Validation Placement

### Decision
Perform request validation in service layer (not in routers).

### Why

- Keeps routers transport-thin and reusable.
- Keeps business validation rules centralized and testable.
- Ensures errors flow through `ValidationException` -> global middleware -> standardized error response.

---

## 7) What Was Deliberately Deferred

Given the time-boxed assessment, the wrapper intentionally defers:

- distributed/shared cache (e.g., Redis)
- persistent idempotency store with TTL and replay windows
- circuit breaker + adaptive backoff policies
- observability stack (metrics/tracing dashboards)
- full tenant adapter resolver implementation (design-ready, not fully built)

These are planned next steps for production hardening.

---

## Summary

The wrapper was designed around four principles:

1. **Modularity** (separable layers)
2. **Standardized error handling** (single exception boundary)
3. **Single-responsibility services** (business logic in services)
4. **Plugin-ready PMS integration boundary** (adapter isolation)

This keeps the external API stable while allowing integration internals to evolve per PMS, tenant, and reliability needs.
