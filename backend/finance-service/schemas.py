from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from models import ApprovalAction


class ApproveRequest(BaseModel):
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    reason: str


class FinanceApprovalResponse(BaseModel):
    id: UUID
    onboarding_request_id: UUID
    notes: Optional[str]
    action: ApprovalAction
    approved_by: UUID
    approved_at: datetime
    rejection_reason: Optional[str]

    model_config = {"from_attributes": True}
