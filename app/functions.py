"""Function stubs as specified in the requirements"""

import asyncio
import random
from typing import Dict, Any
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def flaky_call() -> None:
    """Either raise an error or sleep long enough to trigger an activity timeout."""
    rand_num = random.random()
    logger.debug("Flaky call initiated", rand_num=rand_num)
    
    if rand_num < 0.33:
        logger.warning("Flaky call raising forced failure")
        raise RuntimeError("Forced failure for testing")

    if rand_num < 0.67:
        logger.warning("Flaky call sleeping for 300 seconds")
        await asyncio.sleep(300)  # Expect the activity layer to time out before this completes


async def order_received(order_id: str) -> Dict[str, Any]:
    """Process order reception"""
    await flaky_call()
    # Database write handled by activity
    logger.info("Order received", order_id=order_id)
    return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}]}


async def order_validated(order: Dict[str, Any]) -> bool:
    """Validate order"""
    await flaky_call()
    # Database read/write handled by activity
    if not order.get("items"):
        logger.error("Order validation failed: no items", order=order)
        raise ValueError("No items to validate")
    
    logger.info("Order validated", order_id=order.get("order_id"))
    return True


async def payment_charged(order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    """Charge payment after simulating an error/timeout first.
    Idempotency logic is implemented in the activity.
    """
    await flaky_call()
    # Database read/write handled by activity for idempotency
    amount = sum(i.get("qty", 1) for i in order.get("items", []))
    
    logger.info("Payment charged", order_id=order.get("order_id"), payment_id=payment_id, amount=amount)
    return {"status": "charged", "amount": amount}


async def order_shipped(order: Dict[str, Any]) -> str:
    """Mark order as shipped"""
    await flaky_call()
    # Database write handled by activity
    logger.info("Order shipped", order_id=order.get("order_id"))
    return "Shipped"


async def package_prepared(order: Dict[str, Any]) -> str:
    """Prepare package for shipping"""
    await flaky_call()
    # Database write handled by activity
    logger.info("Package prepared", order_id=order.get("order_id"))
    return "Package ready"


async def carrier_dispatched(order: Dict[str, Any]) -> str:
    """Dispatch to carrier"""
    await flaky_call()
    # Database write handled by activity
    logger.info("Carrier dispatched", order_id=order.get("order_id"))
    return "Dispatched"
