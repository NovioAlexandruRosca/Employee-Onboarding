import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class ProvisionAction(str, enum.Enum):
    completed = "completed"
    rejected = "rejected"


class ITProvision(Base):
    __tablename__ = "it_provisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    onboarding_request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    company_email = Column(String(150), nullable=True)
    account_credentials = Column(Text, nullable=True)
    laptop_config = Column(Text, nullable=True)
    action = Column(SQLEnum(ProvisionAction), nullable=False)
    provisioned_by = Column(UUID(as_uuid=True), nullable=False)
    provisioned_at = Column(DateTime, default=datetime.utcnow)
    rejection_reason = Column(Text, nullable=True)
