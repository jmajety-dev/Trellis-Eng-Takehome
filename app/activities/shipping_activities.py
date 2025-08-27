"""Shipping workflow activities"""

from typing import Dict, Any
from temporalio import activity
from app.database import get_database, DatabaseOperations
from app.functions import package_prepared, carrier_dispatched
from app.utils.logging import get_logger

logger = get_logger(__name__)


@activity.defn
async def prepare_package_activity(order: Dict[str, Any]) -> str:
    """Activity to prepare package for shipping"""
    order_id = order.get("order_id")
    logger.info("Preparing package", order_id=order_id, activity="prepare_package")
    
    try:
        # Call the function stub
        result = await package_prepared(order)
        
        # Database persistence
        async for db in get_database():
            db_ops = DatabaseOperations(db)
            await db_ops.log_event(order_id, "package_prepared", {"result": result},
                                  activity_name="prepare_package_activity")
        
        logger.info("Package prepared successfully", order_id=order_id)
        return result
        
    except Exception as e:
        logger.error("Failed to prepare package", order_id=order_id, error=str(e))
        raise


@activity.defn
async def dispatch_carrier_activity(order: Dict[str, Any]) -> str:
    """Activity to dispatch to carrier"""
    order_id = order.get("order_id")
    logger.info("Dispatching to carrier", order_id=order_id, activity="dispatch_carrier")
    
    try:
        # Call the function stub
        result = await carrier_dispatched(order)
        
        # Database persistence
        async for db in get_database():
            db_ops = DatabaseOperations(db)
            await db_ops.log_event(order_id, "carrier_dispatched", {"result": result},
                                  activity_name="dispatch_carrier_activity")
        
        logger.info("Carrier dispatched successfully", order_id=order_id)
        return result
        
    except Exception as e:
        logger.error("Failed to dispatch carrier", order_id=order_id, error=str(e))
        raise
