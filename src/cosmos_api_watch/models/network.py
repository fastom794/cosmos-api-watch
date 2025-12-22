# models/network.py
from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from cosmos_api_watch.db.session import Base


class Network(Base):
    __tablename__ = "networks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    slug = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    chain_id = Column(String(255), nullable=False)
    network_type = Column(String(20), nullable=False)  # mainnet/testnet

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="networks")
    endpoints = relationship("Endpoint", back_populates="network", cascade="all, delete-orphan")

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

