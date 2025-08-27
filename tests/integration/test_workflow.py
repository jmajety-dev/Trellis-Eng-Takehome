"""Integration tests for the order lifecycle"""

import pytest
import asyncio
from datetime import timedelta
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from app.workflows import OrderWorkflow, ShippingWorkflow
from app.workflows.order_workflow import OrderInput, ApproveOrderSignal
from app.activities import (
    receive_order_activity,
    validate_order_activity,
    charge_payment_activity,
    ship_order_activity,
    prepare_package_activity,
    dispatch_carrier_activity
)
from app.utils.config import settings


class TestOrderWorkflowIntegration:
    """Integration tests for order workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_order_workflow(self):
        """Test complete order workflow execution"""
        async with WorkflowEnvironment() as env:
            # Create task queues
            order_queue = "test-order-queue"
            shipping_queue = "test-shipping-queue"
            
            # Create workers
            order_worker = Worker(
                env.client,
                task_queue=order_queue,
                workflows=[OrderWorkflow],
                activities=[
                    receive_order_activity,
                    validate_order_activity,
                    charge_payment_activity,
                    ship_order_activity
                ]
            )
            
            shipping_worker = Worker(
                env.client,
                task_queue=shipping_queue,
                workflows=[ShippingWorkflow],
                activities=[
                    prepare_package_activity,
                    dispatch_carrier_activity
                ]
            )
            
            async with order_worker, shipping_worker:
                # Start workflow
                workflow_input = OrderInput(
                    order_id="test-order-123",
                    payment_id="payment-456",
                    items=[{"sku": "ABC", "qty": 1}],
                    address={"street": "123 Main St", "city": "Seattle"}
                )
                
                handle = await env.client.start_workflow(
                    OrderWorkflow.run,
                    workflow_input,
                    id="test-order-123",
                    task_queue=order_queue,
                    execution_timeout=timedelta(seconds=30)
                )
                
                # Wait a bit then send approval signal
                await asyncio.sleep(1)
                await handle.signal(OrderWorkflow.approve_order, ApproveOrderSignal())
                
                # Wait for completion
                result = await handle.result()
                
                # Verify result
                assert result["status"] == "completed"
                assert result["order_id"] == "test-order-123"
                assert "payment_result" in result
                assert "shipping_result" in result
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self):
        """Test order cancellation workflow"""
        async with WorkflowEnvironment() as env:
            order_queue = "test-order-queue"
            
            order_worker = Worker(
                env.client,
                task_queue=order_queue,
                workflows=[OrderWorkflow],
                activities=[
                    receive_order_activity,
                    validate_order_activity,
                    charge_payment_activity,
                    ship_order_activity
                ]
            )
            
            async with order_worker:
                workflow_input = OrderInput(
                    order_id="test-cancel-123",
                    payment_id="payment-456",
                    items=[{"sku": "ABC", "qty": 1}]
                )
                
                handle = await env.client.start_workflow(
                    OrderWorkflow.run,
                    workflow_input,
                    id="test-cancel-123",
                    task_queue=order_queue,
                    execution_timeout=timedelta(seconds=30)
                )
                
                # Send cancel signal quickly
                from app.workflows.order_workflow import CancelOrderSignal
                await handle.signal(OrderWorkflow.cancel_order, CancelOrderSignal(reason="User requested"))
                
                # Wait for completion
                result = await handle.result()
                
                # Verify cancellation
                assert result["status"] == "cancelled"
                assert result["order_id"] == "test-cancel-123"
    
    @pytest.mark.asyncio
    async def test_manual_review_timeout(self):
        """Test manual review timeout"""
        async with WorkflowEnvironment() as env:
            order_queue = "test-order-queue"
            
            order_worker = Worker(
                env.client,
                task_queue=order_queue,
                workflows=[OrderWorkflow],
                activities=[
                    receive_order_activity,
                    validate_order_activity,
                    charge_payment_activity,
                    ship_order_activity
                ]
            )
            
            async with order_worker:
                workflow_input = OrderInput(
                    order_id="test-timeout-123",
                    payment_id="payment-456",
                    items=[{"sku": "ABC", "qty": 1}]
                )
                
                handle = await env.client.start_workflow(
                    OrderWorkflow.run,
                    workflow_input,
                    id="test-timeout-123",
                    task_queue=order_queue,
                    execution_timeout=timedelta(seconds=30)
                )
                
                # Don't send approval signal - let it timeout
                result = await handle.result()
                
                # Verify timeout
                assert result["status"] == "timeout"
                assert result["reason"] == "manual_review_timeout"
