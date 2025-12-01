# models/endpoint.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from db.session import Base


class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    network_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)  # rpc/api
    url = Column(String(500), nullable=False, unique=True)

    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    network = relationship("Network", back_populates="endpoints")

    checks = relationship("Check", back_populates="endpoint", cascade="all, delete-orphan")
    status = relationship("EndpointStatus", back_populates="endpoint", uselist=False, cascade="all, delete-orphan")
