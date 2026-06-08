from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from models import HardwareTier, OnboardingStatus


class OnboardingCreate(BaseModel):
    employee_name: str
    role: str
    start_date: str  # ISO date string e.g. "2024-03-01"
    hardware_tier: HardwareTier

    @field_validator("start_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("start_date must be in YYYY-MM-DD format")
        return v


class OnboardingUpdate(BaseModel):
    employee_name: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    hardware_tier: Optional[HardwareTier] = None

    @field_validator("start_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("start_date must be in YYYY-MM-DD format")
        return v


class OnboardingResponse(BaseModel):
    id: UUID
    employee_name: str
    role: str
    start_date: str
    hardware_tier: HardwareTier
    status: OnboardingStatus
    fisa_de_post: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    rejection_reason: Optional[str]
    rejected_by: Optional[UUID]
    rejected_at: Optional[datetime]
    submission_count: int

    model_config = {"from_attributes": True}


class StatusUpdateInternal(BaseModel):
    new_status: OnboardingStatus
    rejection_reason: Optional[str] = None
    rejected_by: Optional[str] = None
