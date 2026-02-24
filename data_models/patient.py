"""Patient API models."""

from pydantic import BaseModel


class PatientResponse(BaseModel):
    """Canonical patient response model returned by wrapper API."""

    patient_id: str
    first_name: str
    last_name: str
    phone: str
    date_of_birth: str | None = None
    has_active_insurance: bool
    last_visit_date: str | None = None
