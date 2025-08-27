"""FastAPI application for order lifecycle system"""

from typing import Dict, Any, List, Optional
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from temporalio.client import Client
from app.workflows.order_workflow import OrderWorkflow, OrderInput, CancelOrderSignal, UpdateAddressSignal, ApproveOrderSignal
from app.database import get_database, DatabaseOperations, check_database_connection
from app.utils.config import settings
from app.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# FastAPI app
app = FastAPI(
    title="Trellis Order Lifecycle System",
    description="Temporal-based order processing system with fault tolerance and idempotency",
    version="1.0.0"
)

# Pydantic models
class OrderStartRequest(BaseModel):
    payment_id: str
    items: List[Dict[str, Any]]
    address: Optional[Dict[str, Any]] = None

class AddressUpdateRequest(BaseModel):
    street: str
    city: str
    state: Optional[str] = None
    zip_code: Optional[str] = None

class CancelOrderRequest(BaseModel):
    reason: str = "User requested cancellation"

class ApprovalRequest(BaseModel):
    approved_by: str = "manual"

# Global Temporal client
temporal_client: Optional[Client] = None

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global temporal_client
    
    logger.info("Starting up application")
    
    # Check database connection
    if not await check_database_connection():
        raise RuntimeError("Database connection failed")
    
    # Initialize Temporal client
    try:
        temporal_client = await Client.connect(settings.temporal_host)
        logger.info("Connected to Temporal server", host=settings.temporal_host)
    except Exception as e:
        logger.error("Failed to connect to Temporal server", error=str(e))
        raise RuntimeError(f"Temporal connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down application")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Trellis Order Lifecycle System", "status": "healthy"}

@app.post("/orders/{order_id}/start")
async def start_order(order_id: str, request: OrderStartRequest) -> Dict[str, Any]:
    """Start an order workflow"""
    logger.info("Starting order workflow", order_id=order_id)
    
    try:
        if not temporal_client:
            raise HTTPException(status_code=500, detail="Temporal client not initialized")
        
        # Create workflow input
        workflow_input = OrderInput(
            order_id=order_id,
            payment_id=request.payment_id,
            items=request.items,
            address=request.address
        )
        
        # Start workflow
        handle = await temporal_client.start_workflow(
            OrderWorkflow.run,
            workflow_input,
            id=f"order-{order_id}",
            task_queue=settings.order_task_queue,
            execution_timeout=timedelta(seconds=settings.workflow_timeout)
        )
        
        logger.info("Order workflow started", order_id=order_id, workflow_id=handle.id)
        
        return {
            "order_id": order_id,
            "workflow_id": handle.id,
            "status": "started",
            "payment_id": request.payment_id
        }
        
    except Exception as e:
        logger.error("Failed to start order workflow", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e}")

@app.post("/orders/{order_id}/signals/cancel")
async def cancel_order(order_id: str, request: CancelOrderRequest) -> Dict[str, Any]:
    """Send cancel signal to order workflow"""
    logger.info("Sending cancel signal", order_id=order_id)
    
    try:
        if not temporal_client:
            raise HTTPException(status_code=500, detail="Temporal client not initialized")
        
        # Get workflow handle
        handle = temporal_client.get_workflow_handle(f"order-{order_id}")
        
        # Send signal
        await handle.signal(OrderWorkflow.cancel_order, CancelOrderSignal(reason=request.reason))
        
        logger.info("Cancel signal sent", order_id=order_id, reason=request.reason)
        
        return {
            "order_id": order_id,
            "signal": "cancel",
            "reason": request.reason,
            "status": "sent"
        }
        
    except Exception as e:
        logger.error("Failed to send cancel signal", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to send signal: {e}")

@app.post("/orders/{order_id}/signals/update-address")
async def update_address(order_id: str, request: AddressUpdateRequest) -> Dict[str, Any]:
    """Send address update signal to order workflow"""
    logger.info("Sending address update signal", order_id=order_id)
    
    try:
        if not temporal_client:
            raise HTTPException(status_code=500, detail="Temporal client not initialized")
        
        # Get workflow handle
        handle = temporal_client.get_workflow_handle(f"order-{order_id}")
        
        # Send signal
        address_data = request.dict()
        await handle.signal(OrderWorkflow.update_address, UpdateAddressSignal(address=address_data))
        
        logger.info("Address update signal sent", order_id=order_id)
        
        return {
            "order_id": order_id,
            "signal": "update_address",
            "new_address": address_data,
            "status": "sent"
        }
        
    except Exception as e:
        logger.error("Failed to send address update signal", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to send signal: {e}")

@app.post("/orders/{order_id}/signals/approve")
async def approve_order(order_id: str, request: ApprovalRequest) -> Dict[str, Any]:
    """Send approval signal to order workflow"""
    logger.info("Sending approval signal", order_id=order_id)
    
    try:
        if not temporal_client:
            raise HTTPException(status_code=500, detail="Temporal client not initialized")
        
        # Get workflow handle
        handle = temporal_client.get_workflow_handle(f"order-{order_id}")
        
        # Send signal
        await handle.signal(OrderWorkflow.approve_order, ApproveOrderSignal(approved_by=request.approved_by))
        
        logger.info("Approval signal sent", order_id=order_id, approved_by=request.approved_by)
        
        return {
            "order_id": order_id,
            "signal": "approve",
            "approved_by": request.approved_by,
            "status": "sent"
        }
        
    except Exception as e:
        logger.error("Failed to send approval signal", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to send signal: {e}")

@app.get("/orders/{order_id}/status")
async def get_order_status(order_id: str, db = Depends(get_database)) -> Dict[str, Any]:
    """Get order status from both workflow and database"""
    logger.info("Getting order status", order_id=order_id)
    
    try:
        # Get database status
        db_ops = DatabaseOperations(db)
        order = await db_ops.get_order(order_id)
        events = await db_ops.get_order_events(order_id, limit=10)
        
        # Get workflow status if available
        workflow_status = None
        if temporal_client:
            try:
                handle = temporal_client.get_workflow_handle(f"order-{order_id}")
                workflow_status = await handle.query(OrderWorkflow.status)
            except Exception as workflow_error:
                logger.warning("Could not get workflow status", order_id=order_id, error=str(workflow_error))
        
        # Combine status information
        status = {
            "order_id": order_id,
            "database_status": {
                "exists": order is not None,
                "state": order.state if order else None,
                "items": order.items if order else None,
                "address": order.address if order else None,
                "created_at": order.created_at.isoformat() if order and order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order and order.updated_at else None
            },
            "workflow_status": workflow_status,
            "recent_events": [
                {
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    "activity_name": event.activity_name
                }
                for event in events
            ]
        }
        
        logger.info("Order status retrieved", order_id=order_id)
        return status
        
    except Exception as e:
        logger.error("Failed to get order status", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")

@app.get("/orders/{order_id}/events")
async def get_order_events(order_id: str, limit: int = 50, db = Depends(get_database)) -> List[Dict[str, Any]]:
    """Get order events from database"""
    logger.info("Getting order events", order_id=order_id, limit=limit)
    
    try:
        db_ops = DatabaseOperations(db)
        events = await db_ops.get_order_events(order_id, limit=limit)
        
        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "payload": event.payload,
                "workflow_id": event.workflow_id,
                "activity_name": event.activity_name,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None
            }
            for event in events
        ]
        
    except Exception as e:
        logger.error("Failed to get order events", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get events: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
