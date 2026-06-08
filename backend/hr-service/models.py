import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class HardwareTier(str, enum.Enum):
    standard = "standard"
    premium = "premium"


class OnboardingStatus(str, enum.Enum):
    initiated = "initiated"
    manager_review = "manager_review"
    finance_review = "finance_review"
    it_provisioning = "it_provisioning"
    completed = "completed"
    needs_rework = "needs_rework"


class OnboardingRequest(Base):
    __tablename__ = "onboarding_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_name = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    start_date = Column(String(20), nullable=False)
    hardware_tier = Column(SQLEnum(HardwareTier), nullable=False)
    status = Column(SQLEnum(OnboardingStatus), nullable=False, default=OnboardingStatus.manager_review)
    fisa_de_post = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(UUID(as_uuid=True), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    submission_count = Column(Integer, default=1, nullable=False)
