#!/usr/bin/env python3
"""Temporal worker startup script"""

import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporalio import Worker
from temporalio.client import Client
from app.workflows import OrderWorkflow, ShippingWorkflow
from app.activities import (
    receive_order_activity,
    validate_order_activity,
    charge_payment_activity,
    ship_order_activity,
    prepare_package_activity,
    dispatch_carrier_activity
)
from app.database import check_database_connection, create_tables
from app.utils.config import settings
from app.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def main():
    """Start Temporal workers"""
    logger.info("Starting Temporal workers")
    
    try:
        # Check database connection and create tables if needed
        if not await check_database_connection():
            logger.error("Database connection failed")
            return 1
        
        try:
            await create_tables()
        except Exception as e:
            logger.warning("Could not create tables (they may already exist)", error=str(e))
        
        # Connect to Temporal server
        logger.info("Connecting to Temporal server", host=settings.temporal_host)
        client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        
        # Create workers for different task queues
        logger.info("Creating workers")
        
        # Order processing worker
        order_worker = Worker(
            client,
            task_queue=settings.order_task_queue,
            workflows=[OrderWorkflow],
            activities=[
                receive_order_activity,
                validate_order_activity,
                charge_payment_activity,
                ship_order_activity
            ]
        )
        
        # Shipping processing worker
        shipping_worker = Worker(
            client,
            task_queue=settings.shipping_task_queue,
            workflows=[ShippingWorkflow],
            activities=[
                prepare_package_activity,
                dispatch_carrier_activity
            ]
        )
        
        logger.info("Starting workers", 
                   order_queue=settings.order_task_queue,
                   shipping_queue=settings.shipping_task_queue)
        
        # Run workers concurrently
        await asyncio.gather(
            order_worker.run(),
            shipping_worker.run()
        )
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        return 0
    except Exception as e:
        logger.error("Worker startup failed", error=str(e))
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
