# models/check.py
from datetime import datetime

from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship

from db.session import Base


class Check(Base):
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False)

    is_available = Column(Boolean, nullable=False)
    status_code = Column(Integer, nullable=True)
    block_delay_ms = Column(Integer, nullable=True)
    last_block_height = Column(String(64), nullable=True)

    error_message = Column(String(500), nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    endpoint = relationship("Endpoint", back_populates="checks")

