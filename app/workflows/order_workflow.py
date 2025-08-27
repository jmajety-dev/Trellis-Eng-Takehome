"""Order workflow implementation"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Any, List, Optional
from temporalio import workflow
from temporalio.common import RetryPolicy
from app.activities.order_activities import (
    receive_order_activity,
    validate_order_activity,
    charge_payment_activity,
    ship_order_activity
)
from app.workflows.shipping_workflow import ShippingWorkflow
from app.utils.config import settings

@dataclass
class OrderInput:
    """Input for order workflow"""
    order_id: str
    payment_id: str
    items: List[Dict[str, Any]]
    address: Optional[Dict[str, Any]] = None

@dataclass 
class CancelOrderSignal:
    """Signal to cancel order"""
    reason: str

@dataclass
class UpdateAddressSignal:
    """Signal to update shipping address"""
    address: Dict[str, Any]

@dataclass
class ApproveOrderSignal:
    """Signal to approve order for payment"""
    approved_by: str = "manual"

@dataclass
class DispatchFailedSignal:
    """Signal from shipping workflow when dispatch fails"""
    reason: str


@workflow.defn
class OrderWorkflow:
    """Main order processing workflow"""
    
    def __init__(self) -> None:
        self.cancelled = False
        self.approved = False
        self.order_data: Optional[Dict[str, Any]] = None
        self.current_address: Optional[Dict[str, Any]] = None
        self.dispatch_failed = False
        self.dispatch_fail_reason = ""
    
    @workflow.run
    async def run(self, input: OrderInput) -> Dict[str, Any]:
        """Main workflow execution"""
        
        # Set workflow timeout
        workflow.logger.info(f"Starting order workflow for {input.order_id}")
        
        try:
            # Step 1: Receive Order
            self.order_data = await workflow.execute_activity(
                receive_order_activity,
                args=[input.order_id, input.items, input.address],
                start_to_close_timeout=timedelta(seconds=settings.activity_timeout),
                retry_policy=self._get_retry_policy()
            )
            self.current_address = input.address
            
            if self.cancelled:
                return {"status": "cancelled", "order_id": input.order_id}
            
            # Step 2: Validate Order
            await workflow.execute_activity(
                validate_order_activity,
                args=[self.order_data],
                start_to_close_timeout=timedelta(seconds=settings.activity_timeout),
                retry_policy=self._get_retry_policy()
            )
            
            if self.cancelled:
                return {"status": "cancelled", "order_id": input.order_id}
            
            # Step 3: Manual Review Timer
            workflow.logger.info(f"Waiting for manual approval for order {input.order_id}")
            
            try:
                await workflow.wait_condition(
                    lambda: self.approved or self.cancelled,
                    timeout=timedelta(seconds=settings.manual_review_timeout)
                )
            except workflow.ConditionTimeoutError:
                workflow.logger.warning(f"Manual review timeout for order {input.order_id}")
                return {"status": "timeout", "order_id": input.order_id, "reason": "manual_review_timeout"}
            
            if self.cancelled:
                return {"status": "cancelled", "order_id": input.order_id}
            
            # Step 4: Charge Payment
            payment_result = await workflow.execute_activity(
                charge_payment_activity,
                args=[self.order_data, input.payment_id],
                start_to_close_timeout=timedelta(seconds=settings.activity_timeout),
                retry_policy=self._get_retry_policy()
            )
            
            if self.cancelled:
                # TODO: Implement payment compensation
                workflow.logger.warning(f"Order cancelled after payment - compensation needed for {input.order_id}")
                return {"status": "cancelled", "order_id": input.order_id, "compensation_needed": True}
            
            # Step 5: Start Shipping Workflow (Child Workflow)
            shipping_result = None
            max_shipping_retries = 3
            shipping_retry = 0
            
            while shipping_retry < max_shipping_retries and not self.cancelled:
                try:
                    # Update order data with current address
                    if self.current_address:
                        self.order_data["address"] = self.current_address
                    
                    shipping_handle = await workflow.start_child_workflow(
                        ShippingWorkflow.run,
                        args=[self.order_data],
                        id=f"shipping-{input.order_id}-{shipping_retry}",
                        task_queue=settings.shipping_task_queue,
                        execution_timeout=timedelta(seconds=settings.workflow_timeout - 5)  # Leave buffer
                    )
                    
                    shipping_result = await shipping_handle
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    workflow.logger.error(f"Shipping workflow failed for order {input.order_id}: {e}")
                    shipping_retry += 1
                    
                    if shipping_retry < max_shipping_retries:
                        workflow.logger.info(f"Retrying shipping workflow for order {input.order_id} (attempt {shipping_retry + 1})")
                        await workflow.sleep(timedelta(seconds=2))  # Brief pause before retry
                    else:
                        workflow.logger.error(f"Shipping workflow failed after {max_shipping_retries} attempts for order {input.order_id}")
                        return {
                            "status": "shipping_failed", 
                            "order_id": input.order_id,
                            "payment_status": "charged",
                            "error": str(e)
                        }
            
            if self.cancelled:
                return {"status": "cancelled", "order_id": input.order_id}
            
            # Step 6: Mark Order as Shipped
            await workflow.execute_activity(
                ship_order_activity,
                args=[self.order_data],
                start_to_close_timeout=timedelta(seconds=settings.activity_timeout),
                retry_policy=self._get_retry_policy()
            )
            
            workflow.logger.info(f"Order workflow completed successfully for {input.order_id}")
            return {
                "status": "completed",
                "order_id": input.order_id,
                "payment_result": payment_result,
                "shipping_result": shipping_result
            }
            
        except Exception as e:
            workflow.logger.error(f"Order workflow failed for {input.order_id}: {e}")
            raise
    
    @workflow.signal
    async def cancel_order(self, signal: CancelOrderSignal) -> None:
        """Signal to cancel order"""
        workflow.logger.info(f"Received cancel signal: {signal.reason}")
        self.cancelled = True
    
    @workflow.signal
    async def update_address(self, signal: UpdateAddressSignal) -> None:
        """Signal to update shipping address"""
        workflow.logger.info(f"Received address update signal")
        self.current_address = signal.address
        
        # Update order data if available
        if self.order_data:
            self.order_data["address"] = signal.address
    
    @workflow.signal
    async def approve_order(self, signal: ApproveOrderSignal) -> None:
        """Signal to approve order for payment"""
        workflow.logger.info(f"Received approval signal from {signal.approved_by}")
        self.approved = True
    
    @workflow.signal
    async def dispatch_failed(self, signal: DispatchFailedSignal) -> None:
        """Signal from shipping workflow when dispatch fails"""
        workflow.logger.warning(f"Received dispatch failed signal: {signal.reason}")
        self.dispatch_failed = True
        self.dispatch_fail_reason = signal.reason
    
    @workflow.query
    def status(self) -> Dict[str, Any]:
        """Query current workflow status"""
        return {
            "cancelled": self.cancelled,
            "approved": self.approved,
            "current_address": self.current_address,
            "dispatch_failed": self.dispatch_failed,
            "order_data": self.order_data
        }
    
    def _get_retry_policy(self) -> RetryPolicy:
        """Get retry policy for activities"""
        return RetryPolicy(
            maximum_attempts=settings.max_retry_attempts,
            initial_interval=timedelta(seconds=settings.initial_retry_interval),
            maximum_interval=timedelta(seconds=settings.max_retry_interval),
            backoff_coefficient=settings.backoff_coefficient,
        )
