import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class ApprovalAction(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"


class FinanceApproval(Base):
    __tablename__ = "finance_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    onboarding_request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    action = Column(SQLEnum(ApprovalAction), nullable=False)
    approved_by = Column(UUID(as_uuid=True), nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow)
    rejection_reason = Column(Text, nullable=True)
