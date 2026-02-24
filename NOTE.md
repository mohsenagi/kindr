# NOTE.md

## Time Breakdown (4-hour assessment)

- **30 min** — Review requirements, high-level planning, module boundaries, architecture decisions.
- **15 min** — Scaffold project and create base modules/packages (`api`, `services`, `data_models`, `tests`, infra wiring).
- **45 min** — Legacy API exploration and behavior discovery (routes, payload formats, failures, quirks), plus evidence capture for exploration notes.
- **35 min** — Implement patient flow end-to-end (`PatientService`, router wiring, normalization, resilience behavior).
- **45 min** — Implement appointment flow end-to-end (`AppointmentService` availability + booking, validation in service layer, idempotency).
- **35 min** — Stabilization and test-driven fixes for flaky/edge behaviors (timeouts, retries, selective caching choices, deterministic idempotency handling under unstable upstream behavior).
- **35 min** — Documentation pass (`ARCHITECTURE.md`, `SYSTEM_DESIGN.md`, and notes refinement).

Total: **240 minutes**

---

## Run Locally

To run the project and tests locally:

- Preferably create and activate a virtual environment.
- Install dependencies:
   - `pip install -r requirements.txt`
- Run API server:
   - `python -m uvicorn api.main:app --host :: --port 3000 --reload`
- Run tests:
   - `pytest`

---

## Immediate Next Steps

1. **Introduce protocols/interfaces + dependency injection**
   - Define `LegacyApiQueryService` protocol as the integration contract.
   - Convert current `DentalTrackApiQueryService` into one concrete implementation.
   - Add DI container + tenant-aware `LegacyApiFactory` to resolve implementation by tenant/subscription/settings.

2. **Move caching to Redis**
   - Replace in-memory caches/idempotency maps with Redis-backed cache + TTL policies.
   - Use differentiated expiry windows by entity type (patient lookup vs availability vs booking/idempotency records).
   - Add cache invalidation/update hooks for booking events.

---

## Additional Next Steps (after immediate)

- Add persistent idempotency storage strategy for multi-instance deployments.
- Add queue-based async retry/dead-letter handling for write operations during outages.
- Add observability (metrics, tracing, structured logs, SLO dashboards).
- Build on-prem local agent + outbound tunnel proof-of-concept for Dentrix connector path.
