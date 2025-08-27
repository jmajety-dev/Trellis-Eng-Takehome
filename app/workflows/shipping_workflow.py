"""Shipping workflow implementation"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy
from app.activities.shipping_activities import (
    prepare_package_activity,
    dispatch_carrier_activity
)
from app.utils.config import settings


@workflow.defn
class ShippingWorkflow:
    """Child workflow for shipping operations"""
    
    @workflow.run
    async def run(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Shipping workflow execution"""
        order_id = order.get("order_id")
        workflow.logger.info(f"Starting shipping workflow for order {order_id}")
        
        try:
            # Step 1: Prepare Package
            package_result = await workflow.execute_activity(
                prepare_package_activity,
                args=[order],
                start_to_close_timeout=timedelta(seconds=settings.activity_timeout),
                retry_policy=self._get_retry_policy()
            )
            
            # Step 2: Dispatch to Carrier
            try:
                dispatch_result = await workflow.execute_activity(
                    dispatch_carrier_activity,
                    args=[order],
                    start_to_close_timeout=timedelta(seconds=settings.activity_timeout),
                    retry_policy=self._get_retry_policy()
                )
                
                workflow.logger.info(f"Shipping workflow completed successfully for order {order_id}")
                return {
                    "status": "dispatched",
                    "order_id": order_id,
                    "package_result": package_result,
                    "dispatch_result": dispatch_result
                }
                
            except Exception as dispatch_error:
                workflow.logger.error(f"Dispatch failed for order {order_id}: {dispatch_error}")
                
                # Signal parent workflow about dispatch failure
                try:
                    parent_handle = workflow.get_external_workflow_handle(
                        workflow_id=f"order-{order_id}",
                        workflow_type="OrderWorkflow"
                    )
                    
                    from app.workflows.order_workflow import DispatchFailedSignal
                    await parent_handle.signal(
                        "dispatch_failed",
                        DispatchFailedSignal(reason=str(dispatch_error))
                    )
                except Exception as signal_error:
                    workflow.logger.error(f"Failed to signal parent workflow: {signal_error}")
                
                # Re-raise the dispatch error for parent workflow to handle
                raise dispatch_error
                
        except Exception as e:
            workflow.logger.error(f"Shipping workflow failed for order {order_id}: {e}")
            raise
    
    def _get_retry_policy(self) -> RetryPolicy:
        """Get retry policy for activities"""
        return RetryPolicy(
            maximum_attempts=settings.max_retry_attempts,
            initial_interval=timedelta(seconds=settings.initial_retry_interval),
            maximum_interval=timedelta(seconds=settings.max_retry_interval),
            backoff_coefficient=settings.backoff_coefficient,
        )
