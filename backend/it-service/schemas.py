from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from models import ProvisionAction


class CompleteProvisionRequest(BaseModel):
    company_email: str
    account_credentials: str
    laptop_config: str

    @field_validator("company_email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v


class RejectRequest(BaseModel):
    reason: str


class ITProvisionResponse(BaseModel):
    id: UUID
    onboarding_request_id: UUID
    company_email: Optional[str]
    account_credentials: Optional[str]
    laptop_config: Optional[str]
    action: ProvisionAction
    provisioned_by: UUID
    provisioned_at: datetime
    rejection_reason: Optional[str]

    model_config = {"from_attributes": True}
