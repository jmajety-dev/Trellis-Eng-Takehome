"""Database models"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, DateTime, Text, Integer, JSON, Boolean
from sqlalchemy.sql import func
from .connection import Base


class Order(Base):
    """Order model for tracking order lifecycle"""
    
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True)
    state = Column(String, nullable=False, default="received")
    items = Column(JSON, nullable=False)
    address = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Order(id={self.id}, state={self.state})>"


class Payment(Base):
    """Payment model with idempotency support"""
    
    __tablename__ = "payments"
    
    payment_id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    amount = Column(Integer, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Payment(payment_id={self.payment_id}, order_id={self.order_id}, status={self.status})>"


class Event(Base):
    """Event model for audit trail and debugging"""
    
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    workflow_id = Column(String, nullable=True)
    activity_name = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Event(id={self.id}, order_id={self.order_id}, event_type={self.event_type})>"
