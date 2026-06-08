import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class ReviewAction(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"


class ManagerReview(Base):
    __tablename__ = "manager_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    onboarding_request_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    fisa_de_post_notes = Column(Text, nullable=True)
    action = Column(SQLEnum(ReviewAction), nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), nullable=False)
    reviewed_at = Column(DateTime, default=datetime.utcnow)
    rejection_reason = Column(Text, nullable=True)
