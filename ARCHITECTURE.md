# Architecture Documentation

## System Overview

The Trellis Order Lifecycle System is built using Temporal for workflow orchestration, providing fault-tolerant order processing with the following key components:

- **OrderWorkflow**: Main workflow handling order reception, validation, manual review, payment, and shipping coordination
- **ShippingWorkflow**: Child workflow managing package preparation and carrier dispatch
- **Database Layer**: PostgreSQL with idempotency support
- **API Layer**: FastAPI for external interactions
- **Activities**: Temporal activities that call business logic functions

## Workflow Architecture

### OrderWorkflow Flow

```
Order Received → Order Validated → Manual Review Timer → Payment Charged → Shipping Started → Order Shipped
       ↓                ↓                    ↓                   ↓               ↓              ↓
   DB: Insert       DB: Update         Wait for Signal      DB: Payment     Child Workflow   DB: Update
   Order Record     Status             (10s timeout)       Processing      (Separate Queue) Status
```

### Signal Handling

The system supports several signals for dynamic control:

1. **approve**: Manual approval to proceed with payment
2. **cancel**: Cancel the order (before shipping starts)
3. **update-address**: Update shipping address before dispatch
4. **dispatch-failed**: Internal signal from shipping workflow

### Time Constraints

- **Total Workflow**: 15 seconds maximum
- **Manual Review**: 10 seconds timeout
- **Activity Timeout**: 5 seconds with retries
- **Retry Policy**: Exponential backoff with 3 attempts

## Database Schema

### Tables

```sql
-- Orders table
CREATE TABLE orders (
    id VARCHAR PRIMARY KEY,
    state VARCHAR NOT NULL DEFAULT 'received',
    items JSON NOT NULL,
    address JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payments table (idempotency)
CREATE TABLE payments (
    payment_id VARCHAR PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    amount INTEGER NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Events table (audit trail)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    payload JSON,
    workflow_id VARCHAR,
    activity_name VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Idempotency Strategy

**Payment Processing**: Uses PostgreSQL's `ON CONFLICT DO NOTHING` to ensure payment records are created idempotently. The `processed` flag prevents double-charging.

**Event Logging**: All significant events are logged with timestamps for debugging and audit trails.

## Task Queue Isolation

- **order-processing**: Handles OrderWorkflow and its activities
- **shipping-processing**: Handles ShippingWorkflow and shipping activities

This separation allows:
- Independent scaling of different workflow types
- Isolation of failures
- Team-based development and deployment

## Fault Tolerance

### Activity Retries

All activities use exponential backoff retry policy:
- Maximum attempts: 3
- Initial interval: 1 second
- Maximum interval: 10 seconds
- Backoff coefficient: 2.0

### Error Handling

The `flaky_call()` function simulates realistic failures:
- 33% chance of immediate failure
- 33% chance of timeout (300s sleep)
- 33% chance of success

### Compensation

When orders are cancelled after payment, the system flags the need for compensation (refund processing would be implemented here).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/orders/{order_id}/start` | Start order workflow |
| POST | `/orders/{order_id}/signals/cancel` | Cancel order |
| POST | `/orders/{order_id}/signals/approve` | Approve order |
| POST | `/orders/{order_id}/signals/update-address` | Update address |
| GET | `/orders/{order_id}/status` | Get order status |
| GET | `/orders/{order_id}/events` | Get order events |

## Observability

### Logging

Structured JSON logging with:
- Order ID correlation
- Activity names
- Error details
- Retry attempts
- State transitions

### Monitoring

- **Temporal Web UI**: Workflow execution history and current state
- **Database Events**: Complete audit trail of all operations
- **API Status Endpoints**: Real-time status queries combining workflow and database state

### Debugging

- Event sourcing provides complete operation history
- Workflow replays show exact execution path
- Database logs capture all state changes

## Security Considerations

- Database connections use connection pooling
- API endpoints validate input data
- Idempotency prevents double-processing
- Error messages don't expose sensitive data

## Scaling Considerations

- **Horizontal**: Multiple workers can run on different machines
- **Task Queue Separation**: Different teams can manage different workflow types
- **Database Connection Pooling**: Handles concurrent access efficiently
- **Temporal Sharding**: Can scale to millions of workflows

## Testing Strategy

### Unit Tests
- Function stub behavior
- Database operations
- Idempotency logic

### Integration Tests
- Complete workflow execution
- Signal handling
- Timeout scenarios
- Cancellation flows

### Load Testing
- Multiple concurrent workflows
- Database performance under load
- Temporal server capacity

This architecture provides a robust, scalable foundation for order processing that can handle failures gracefully while maintaining data consistency and providing clear observability into system behavior.
