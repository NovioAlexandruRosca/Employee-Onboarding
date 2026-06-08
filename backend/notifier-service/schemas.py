from typing import List, Optional

from pydantic import BaseModel


class NotifyPayload(BaseModel):
    event: str
    onboarding_request_id: str
    employee_name: str
    old_status: str
    new_status: str
    target_roles: List[str]
    message: str
    rejection_reason: Optional[str] = None
