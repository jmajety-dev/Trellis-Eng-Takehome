# Trellis Temporal Order Lifecycle System

A robust order processing system built with Temporal for workflow orchestration, featuring fault tolerance, idempotency, and database persistence. This implementation demonstrates production-ready patterns for complex workflow orchestration as requested in the Trellis Engineering take-home assignment.

## Architecture

- **OrderWorkflow**: Main workflow handling order processing with manual review timer
- **ShippingWorkflow**: Child workflow for package preparation and dispatch on separate task queue  
- **Database**: PostgreSQL for persistence with idempotency guarantees
- **API**: FastAPI for workflow triggers and status queries
- **Activities**: Temporal activities calling the provided function stubs with `flaky_call()`

## Key Features

- **15-second workflow completion** within time constraint
- **Manual review timer** with 10-second timeout and signal-based approval
- **Idempotent payment processing** using unique payment IDs
- **Signal handling** for cancellation, address updates, and approval
- **Child workflows** on separate task queues for shipping
- **Fault tolerance** with exponential backoff retries
- **Database persistence** with complete audit trail
- **Real-time monitoring** via Temporal Web UI and API endpoints

## Quick Start

### Automated Setup (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd Trellis-Eng-Takehome

# Run automated setup
./scripts/setup.sh

# Start API server (in new terminal)
make api

# Run complete demo
make demo
```

### Manual Setup

If you prefer step-by-step setup or need to troubleshoot:

1. **Start Infrastructure**:
```bash
docker-compose up -d
```

2. **Install Dependencies & Migrate**:
```bash
pip install -r requirements.txt
python scripts/migrate.py
```

3. **Start API**:
```bash
python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

4. **Test System**:
```bash
python scripts/health_check.py
```

## Usage Examples

### REST API

```bash
# Start an order
curl -X POST "http://localhost:8000/orders/order-123/start" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pay-456",
    "items": [{"sku": "ABC", "qty": 2}],
    "address": {"street": "123 Main St", "city": "Seattle"}
  }'

# Check status
curl "http://localhost:8000/orders/order-123/status"

# Approve order (must be within 10 seconds)
curl -X POST "http://localhost:8000/orders/order-123/signals/approve" \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "manager"}'

# Cancel order
curl -X POST "http://localhost:8000/orders/order-123/signals/cancel" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer requested"}'

# Update address
curl -X POST "http://localhost:8000/orders/order-123/signals/update-address" \
  -H "Content-Type: application/json" \
  -d '{"street": "456 Oak Ave", "city": "Portland"}'
```

### CLI Commands

```bash
# Start order
python scripts/cli.py start order-456 payment-789 '[{"sku":"XYZ","qty":1}]' --address '{"street":"123 Main","city":"NYC"}'

# Check status
python scripts/cli.py status order-456

# Send signals
python scripts/cli.py signal order-456 approve --data "CLI approval"
python scripts/cli.py signal order-456 cancel --data "Test cancellation"
python scripts/cli.py signal order-456 update-address --data '{"street":"New Address","city":"Boston"}'
```

### Make Commands

```bash
# Infrastructure
make up              # Start all services
make down           # Stop all services
make logs           # View logs
make clean          # Clean up volumes

# Testing
make demo           # Run complete demo workflow
make start-order    # Start example order
make approve-order  # Approve example order
make order-status   # Check example order status

# Development
make install        # Install dependencies
make migrate        # Run database migrations
make test           # Run all tests
make api            # Start API server
```

## Project Structure

```
├── app/
│   ├── api.py              # FastAPI endpoints
│   ├── functions.py        # Required function stubs with flaky_call()
│   ├── activities/         # Temporal activities
│   │   ├── order_activities.py     # Order processing activities
│   │   └── shipping_activities.py  # Shipping activities
│   ├── workflows/          # Temporal workflows
│   │   ├── order_workflow.py       # Main OrderWorkflow
│   │   └── shipping_workflow.py    # Child ShippingWorkflow
│   ├── database/           # Database layer
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── operations.py          # Database operations
│   │   └── connection.py          # DB connection setup
│   └── utils/              # Configuration and logging
├── scripts/
│   ├── setup.sh           # Automated setup script
│   ├── migrate.py         # Database migration
│   ├── worker.py          # Temporal worker startup
│   ├── cli.py             # Command-line interface
│   └── health_check.py    # System health verification
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docker-compose.yml     # Infrastructure setup
├── Makefile              # Development commands
├── ARCHITECTURE.md       # Detailed architecture docs
├── DEPLOYMENT.md         # Deployment guide
└── README.md
```

## Implementation Details

### Workflow Design

**OrderWorkflow** (`15-second completion target`):
1. **Receive Order** → Database insert
2. **Validate Order** → Business validation
3. **Manual Review Timer** → 10-second wait for approval signal
4. **Charge Payment** → Idempotent payment processing
5. **Start Shipping** → Child workflow on separate queue
6. **Mark Shipped** → Final status update

**ShippingWorkflow** (Child workflow):
1. **Prepare Package** → Packaging simulation
2. **Dispatch Carrier** → Carrier integration simulation

### Signal Handling

- **`approve`**: Manual approval to proceed with payment
- **`cancel`**: Cancel order (with compensation logic for post-payment)
- **`update-address`**: Update shipping address before dispatch
- **`dispatch-failed`**: Internal signal from shipping workflow failures

### Idempotency Strategy

**Payment Processing**: Uses PostgreSQL `ON CONFLICT DO NOTHING` with unique `payment_id` to prevent double-charging. The `processed` boolean flag ensures payments are only processed once.

**Database Operations**: All state changes are logged with timestamps for complete audit trail and debugging.

### Function Stubs Integration

All activities call the required function stubs:
- `order_received()`, `order_validated()`, `payment_charged()`
- `order_shipped()`, `package_prepared()`, `carrier_dispatched()`
- Each function calls `flaky_call()` for failure simulation
- Database persistence handled by activities for idempotency

## Monitoring & Observability

### Real-time Monitoring
- **Temporal Web UI**: http://localhost:8080 (workflow execution, retries, history)
- **API Documentation**: http://localhost:8000/docs (interactive API docs)
- **Health Check**: `python scripts/health_check.py`

### Logging & Debugging
- **Structured JSON logging** with order ID correlation
- **Complete audit trail** in database events table
- **Activity retry tracking** with exponential backoff
- **Workflow state queries** via API endpoints

### Development Tools
```bash
# View real-time logs
docker-compose logs -f worker

# Database inspection
docker-compose exec app-postgres psql -U app_user -d orders

# Check specific order events
curl "http://localhost:8000/orders/order-123/events"
```

## Testing

```bash
# Run all tests
make test

# Unit tests only
make test-unit

# Integration tests (requires running infrastructure)
make test-integration

# Manual testing
make demo                    # Complete workflow demo
python scripts/health_check.py  # System health verification
```

## Requirements Compliance

 **All Core Requirements Met**:

- **Temporal SDK**: Uses open-source Temporal Python SDK
- **Function Stubs**: All required functions implemented with `flaky_call()`
- **OrderWorkflow**: Main workflow with signals, timers, child workflows
- **ShippingWorkflow**: Child workflow on separate task queue
- **15-second completion**: Workflow completes within time constraint
- **Manual Review**: 10-second timer with signal-based approval
- **Database**: Real PostgreSQL with migrations and idempotency
- **CLI/API**: FastAPI endpoints + CLI tool for all operations
- **Local Setup**: Docker Compose for complete local development
- **Testing**: Unit and integration tests with Temporal testing framework
- **Observability**: Structured logging, monitoring, and status queries

**Signal Support**:
- `CancelOrder` - cancels before shipment
- `UpdateAddress` - updates shipping address
- `ApproveOrder` - manual approval signal
- `DispatchFailed` - internal shipping failure signal

**Technical Implementation**:
- **Idempotent payments** with unique payment IDs
- **Separate task queues** for workflow isolation
- **Retry policies** with exponential backoff
- **Database persistence** with complete audit trail
- **Error simulation** via `flaky_call()` in all functions
- **Compensation logic** for cancelled orders after payment

## Additional Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Detailed system architecture and design decisions
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Comprehensive deployment and troubleshooting guide

## Summary

This implementation provides a production-ready order lifecycle system using Temporal for workflow orchestration. It demonstrates fault tolerance, idempotency, proper error handling, and observability while meeting all the specified requirements including the 15-second completion constraint and comprehensive signal handling.
