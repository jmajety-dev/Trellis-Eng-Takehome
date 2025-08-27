#!/usr/bin/env python3
"""CLI tool for managing the order lifecycle system"""

import asyncio
import sys
import os
import argparse
import json
from typing import Dict, Any

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporalio.client import Client
from app.workflows.order_workflow import OrderWorkflow, OrderInput, CancelOrderSignal, UpdateAddressSignal, ApproveOrderSignal
from app.utils.config import settings
from app.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def start_order(order_id: str, payment_id: str, items: str, address: str = None):
    """Start an order workflow"""
    try:
        # Parse items JSON
        items_data = json.loads(items)
        address_data = json.loads(address) if address else None
        
        # Connect to Temporal
        client = await Client.connect(settings.temporal_host)
        
        # Create workflow input
        workflow_input = OrderInput(
            order_id=order_id,
            payment_id=payment_id,
            items=items_data,
            address=address_data
        )
        
        # Start workflow
        handle = await client.start_workflow(
            OrderWorkflow.run,
            workflow_input,
            id=f"order-{order_id}",
            task_queue=settings.order_task_queue
        )
        
        print(f"Order workflow started: {handle.id}")
        return 0
        
    except Exception as e:
        print(f"Failed to start order: {e}")
        return 1


async def send_signal(order_id: str, signal_type: str, data: str = None):
    """Send a signal to an order workflow"""
    try:
        # Connect to Temporal
        client = await Client.connect(settings.temporal_host)
        
        # Get workflow handle
        handle = client.get_workflow_handle(f"order-{order_id}")
        
        # Send appropriate signal
        if signal_type == "cancel":
            reason = data if data else "CLI cancellation"
            await handle.signal(OrderWorkflow.cancel_order, CancelOrderSignal(reason=reason))
            print(f"Cancel signal sent to order {order_id}")
            
        elif signal_type == "approve":
            approved_by = data if data else "CLI"
            await handle.signal(OrderWorkflow.approve_order, ApproveOrderSignal(approved_by=approved_by))
            print(f"Approval signal sent to order {order_id}")
            
        elif signal_type == "update-address":
            if not data:
                raise ValueError("Address data required for update-address signal")
            address_data = json.loads(data)
            await handle.signal(OrderWorkflow.update_address, UpdateAddressSignal(address=address_data))
            print(f"Address update signal sent to order {order_id}")
            
        else:
            raise ValueError(f"Unknown signal type: {signal_type}")
        
        return 0
        
    except Exception as e:
        print(f"Failed to send signal: {e}")
        return 1


async def get_status(order_id: str):
    """Get order status"""
    try:
        # Connect to Temporal
        client = await Client.connect(settings.temporal_host)
        
        # Get workflow handle
        handle = client.get_workflow_handle(f"order-{order_id}")
        
        # Query status
        status = await handle.query(OrderWorkflow.status)
        
        print(f"Order {order_id} status:")
        print(json.dumps(status, indent=2))
        return 0
        
    except Exception as e:
        print(f"Failed to get status: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Trellis Order Lifecycle CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start order command
    start_parser = subparsers.add_parser("start", help="Start an order workflow")
    start_parser.add_argument("order_id", help="Order ID")
    start_parser.add_argument("payment_id", help="Payment ID")
    start_parser.add_argument("items", help="Items JSON (e.g., '[{\"sku\":\"ABC\",\"qty\":1}]')")
    start_parser.add_argument("--address", help="Address JSON (optional)")
    
    # Signal command
    signal_parser = subparsers.add_parser("signal", help="Send signal to order workflow")
    signal_parser.add_argument("order_id", help="Order ID")
    signal_parser.add_argument("signal_type", choices=["cancel", "approve", "update-address"], help="Signal type")
    signal_parser.add_argument("--data", help="Signal data (JSON for update-address, text for others)")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get order status")
    status_parser.add_argument("order_id", help="Order ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "start":
        return asyncio.run(start_order(args.order_id, args.payment_id, args.items, args.address))
    elif args.command == "signal":
        return asyncio.run(send_signal(args.order_id, args.signal_type, args.data))
    elif args.command == "status":
        return asyncio.run(get_status(args.order_id))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
