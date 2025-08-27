"""Database operations for order lifecycle"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.utils.logging import get_logger
from .models import Order, Payment, Event

logger = get_logger(__name__)


class DatabaseOperations:
    """Database operations with idempotency support"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_order(self, order_id: str, items: List[Dict[str, Any]], address: Optional[Dict[str, Any]] = None) -> Order:
        """Create a new order"""
        try:
            order = Order(
                id=order_id,
                state="received",
                items=items,
                address=address
            )
            self.session.add(order)
            await self.session.flush()
            
            # Log event
            await self.log_event(order_id, "order_created", {"items": items, "address": address})
            
            logger.info("Order created", order_id=order_id)
            return order
            
        except Exception as e:
            logger.error("Failed to create order", order_id=order_id, error=str(e))
            raise
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        try:
            result = await self.session.execute(
                select(Order).where(Order.id == order_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get order", order_id=order_id, error=str(e))
            raise
    
    async def update_order_state(self, order_id: str, state: str) -> bool:
        """Update order state"""
        try:
            result = await self.session.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(state=state, updated_at=datetime.utcnow())
            )
            
            if result.rowcount > 0:
                await self.log_event(order_id, "state_changed", {"new_state": state})
                logger.info("Order state updated", order_id=order_id, state=state)
                return True
            return False
            
        except Exception as e:
            logger.error("Failed to update order state", order_id=order_id, state=state, error=str(e))
            raise
    
    async def update_order_address(self, order_id: str, address: Dict[str, Any]) -> bool:
        """Update order shipping address"""
        try:
            result = await self.session.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(address=address, updated_at=datetime.utcnow())
            )
            
            if result.rowcount > 0:
                await self.log_event(order_id, "address_updated", {"new_address": address})
                logger.info("Order address updated", order_id=order_id)
                return True
            return False
            
        except Exception as e:
            logger.error("Failed to update order address", order_id=order_id, error=str(e))
            raise
    
    async def create_or_get_payment(self, payment_id: str, order_id: str, amount: int) -> Payment:
        """Create payment with idempotency (upsert)"""
        try:
            # Use PostgreSQL's ON CONFLICT for idempotency
            stmt = pg_insert(Payment).values(
                payment_id=payment_id,
                order_id=order_id,
                status="pending",
                amount=amount,
                processed=False
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=['payment_id'])
            
            await self.session.execute(stmt)
            await self.session.flush()
            
            # Get the payment record
            result = await self.session.execute(
                select(Payment).where(Payment.payment_id == payment_id)
            )
            payment = result.scalar_one()
            
            logger.info("Payment record ensured", payment_id=payment_id, order_id=order_id)
            return payment
            
        except Exception as e:
            logger.error("Failed to create/get payment", payment_id=payment_id, order_id=order_id, error=str(e))
            raise
    
    async def process_payment(self, payment_id: str) -> bool:
        """Mark payment as processed (idempotent)"""
        try:
            result = await self.session.execute(
                update(Payment)
                .where(Payment.payment_id == payment_id)
                .where(Payment.processed == False)  # Only update if not already processed
                .values(status="charged", processed=True, updated_at=datetime.utcnow())
            )
            
            if result.rowcount > 0:
                # Get payment for logging
                payment_result = await self.session.execute(
                    select(Payment).where(Payment.payment_id == payment_id)
                )
                payment = payment_result.scalar_one()
                
                await self.log_event(payment.order_id, "payment_processed", {"payment_id": payment_id})
                logger.info("Payment processed", payment_id=payment_id, order_id=payment.order_id)
                return True
            else:
                logger.info("Payment already processed", payment_id=payment_id)
                return True  # Already processed is considered success
                
        except Exception as e:
            logger.error("Failed to process payment", payment_id=payment_id, error=str(e))
            raise
    
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        try:
            result = await self.session.execute(
                select(Payment).where(Payment.payment_id == payment_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get payment", payment_id=payment_id, error=str(e))
            raise
    
    async def log_event(self, order_id: str, event_type: str, payload: Optional[Dict[str, Any]] = None, 
                       workflow_id: Optional[str] = None, activity_name: Optional[str] = None) -> Event:
        """Log an event for audit trail"""
        try:
            event = Event(
                order_id=order_id,
                event_type=event_type,
                payload=payload,
                workflow_id=workflow_id,
                activity_name=activity_name
            )
            self.session.add(event)
            await self.session.flush()
            
            logger.debug("Event logged", order_id=order_id, event_type=event_type)
            return event
            
        except Exception as e:
            logger.error("Failed to log event", order_id=order_id, event_type=event_type, error=str(e))
            raise
    
    async def get_order_events(self, order_id: str, limit: int = 50) -> List[Event]:
        """Get events for an order"""
        try:
            result = await self.session.execute(
                select(Event)
                .where(Event.order_id == order_id)
                .order_by(Event.timestamp.desc())
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get order events", order_id=order_id, error=str(e))
            raise
