from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from models import ReviewAction


class ApproveRequest(BaseModel):
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    reason: str


class ManagerReviewResponse(BaseModel):
    id: UUID
    onboarding_request_id: UUID
    fisa_de_post_notes: Optional[str]
    action: ReviewAction
    reviewed_by: UUID
    reviewed_at: datetime
    rejection_reason: Optional[str]

    model_config = {"from_attributes": True}
