"""Order processing activities"""

from typing import Dict, Any, List, Optional
from temporalio import activity
from app.database import get_database, DatabaseOperations
from app.functions import order_received, order_validated, payment_charged, order_shipped
from app.utils.logging import get_logger

logger = get_logger(__name__)


@activity.defn
async def receive_order_activity(order_id: str, items: List[Dict[str, Any]], address: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Activity to receive and persist order"""
    logger.info("Receiving order", order_id=order_id, activity="receive_order")
    
    try:
        # Call the function stub
        result = await order_received(order_id)
        
        # Database persistence
        async for db in get_database():
            db_ops = DatabaseOperations(db)
            await db_ops.create_order(order_id, items, address)
            await db_ops.log_event(order_id, "order_received", {"items": items, "address": address}, 
                                  activity_name="receive_order_activity")
        
        logger.info("Order received successfully", order_id=order_id)
        return {"order_id": order_id, "items": items, "address": address}
        
    except Exception as e:
        logger.error("Failed to receive order", order_id=order_id, error=str(e))
        raise


@activity.defn
async def validate_order_activity(order: Dict[str, Any]) -> bool:
    """Activity to validate order"""
    order_id = order.get("order_id")
    logger.info("Validating order", order_id=order_id, activity="validate_order")
    
    try:
        # Call the function stub
        result = await order_validated(order)
        
        # Database persistence
        async for db in get_database():
            db_ops = DatabaseOperations(db)
            await db_ops.update_order_state(order_id, "validated")
            await db_ops.log_event(order_id, "order_validated", {"validation_result": result},
                                  activity_name="validate_order_activity")
        
        logger.info("Order validated successfully", order_id=order_id)
        return result
        
    except Exception as e:
        logger.error("Failed to validate order", order_id=order_id, error=str(e))
        raise


@activity.defn
async def charge_payment_activity(order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    """Activity to charge payment with idempotency"""
    order_id = order.get("order_id")
    logger.info("Charging payment", order_id=order_id, payment_id=payment_id, activity="charge_payment")
    
    try:
        # Calculate amount
        amount = sum(i.get("qty", 1) for i in order.get("items", []))
        
        # Database idempotency check
        async for db in get_database():
            db_ops = DatabaseOperations(db)
            
            # Create or get payment record (idempotent)
            payment = await db_ops.create_or_get_payment(payment_id, order_id, amount)
            
            # Check if already processed
            if payment.processed:
                logger.info("Payment already processed", payment_id=payment_id, order_id=order_id)
                return {"status": "charged", "amount": amount}
            
            # Call the function stub (may fail)
            result = await payment_charged(order, payment_id)
            
            # Mark as processed (idempotent)
            await db_ops.process_payment(payment_id)
            await db_ops.update_order_state(order_id, "payment_charged")
            await db_ops.log_event(order_id, "payment_charged", {"payment_id": payment_id, "amount": amount},
                                  activity_name="charge_payment_activity")
        
        logger.info("Payment charged successfully", order_id=order_id, payment_id=payment_id)
        return result
        
    except Exception as e:
        logger.error("Failed to charge payment", order_id=order_id, payment_id=payment_id, error=str(e))
        raise


@activity.defn
async def ship_order_activity(order: Dict[str, Any]) -> str:
    """Activity to mark order as shipped"""
    order_id = order.get("order_id")
    logger.info("Shipping order", order_id=order_id, activity="ship_order")
    
    try:
        # Call the function stub
        result = await order_shipped(order)
        
        # Database persistence
        async for db in get_database():
            db_ops = DatabaseOperations(db)
            await db_ops.update_order_state(order_id, "shipped")
            await db_ops.log_event(order_id, "order_shipped", {"result": result},
                                  activity_name="ship_order_activity")
        
        logger.info("Order shipped successfully", order_id=order_id)
        return result
        
    except Exception as e:
        logger.error("Failed to ship order", order_id=order_id, error=str(e))
        raise
