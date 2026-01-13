from pydantic import BaseModel

class DistrictRisk(BaseModel):
    district: str
    state: str
    date: str
    ciim: float
    biometric_intensity: float
    child_bio_ratio: float
    bio_growth: float
