# Deployment Guide

## Quick Start (Recommended)

The fastest way to get started is using the provided setup script:

```bash
# Clone and enter the repository
git clone <your-repo-url>
cd Trellis-Eng-Takehome

# Run the automated setup
./scripts/setup.sh

# Start the API server in a new terminal
make api

# Run a demo workflow
make demo
```

## Manual Setup

If you prefer to set up manually or need to troubleshoot:

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Make (optional, for convenience commands)

### Step 1: Infrastructure Setup

```bash
# Start Temporal server and PostgreSQL
docker-compose up -d

# Check that services are running
docker-compose ps
```

Expected output:
```
NAME                           STATUS
trellis-eng-takehome-temporal-1    running
trellis-eng-takehome-postgres-1    running
trellis-eng-takehome-app-postgres-1 running
trellis-eng-takehome-worker-1      running
```

### Step 2: Python Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### Step 3: Database Setup

```bash
# Wait for PostgreSQL to be ready (check logs)
docker-compose logs app-postgres

# Run migrations
python scripts/migrate.py
```

### Step 4: Verify Setup

```bash
# Check system health
python scripts/health_check.py

# Expected output:
# 🗄️  Testing database connection...
# ✅ Database connection successful
# ✅ Database tables created/verified
# ⏰ Testing Temporal connection...
# ✅ Temporal connection successful
# 🎉 All systems are ready!
```

### Step 5: Start API Server

```bash
# Start FastAPI server
python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

## Testing the System

### Using the API

1. **Start an order**:
```bash
curl -X POST "http://localhost:8000/orders/order-123/start" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pay-456",
    "items": [{"sku": "ABC", "qty": 2}],
    "address": {"street": "123 Main St", "city": "Seattle"}
  }'
```

2. **Check status**:
```bash
curl "http://localhost:8000/orders/order-123/status"
```

3. **Approve the order** (within 10 seconds):
```bash
curl -X POST "http://localhost:8000/orders/order-123/signals/approve" \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "test_user"}'
```

### Using the CLI Tool

```bash
# Start an order
python scripts/cli.py start order-456 payment-789 '[{"sku":"XYZ","qty":1}]'

# Check status
python scripts/cli.py status order-456

# Send approval
python scripts/cli.py signal order-456 approve --data "CLI approval"

# Cancel if needed
python scripts/cli.py signal order-456 cancel --data "Test cancellation"
```

### Using Make Commands

```bash
# Complete demo workflow
make demo

# Individual commands
make start-order
make approve-order
make order-status
```

## Monitoring and Debugging

### Temporal Web UI

Visit http://localhost:8080 to see:
- Active workflows
- Workflow history
- Retry attempts
- Activity execution details

### Application Logs

```bash
# View worker logs
docker-compose logs -f worker

# View all logs
docker-compose logs -f
```

### Database Inspection

```bash
# Connect to the database
docker-compose exec app-postgres psql -U app_user -d orders

# View orders
SELECT * FROM orders;

# View events
SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;

# View payments
SELECT * FROM payments;
```

### API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

## Common Issues and Solutions

### Services Won't Start

**Problem**: Docker containers fail to start
**Solution**: 
```bash
# Clean up and restart
make clean
make up
```

### Database Connection Errors

**Problem**: "could not connect to server"
**Solution**:
```bash
# Check if PostgreSQL is ready
docker-compose logs app-postgres

# Wait for the healthy status
docker-compose ps
```

### Temporal Connection Errors

**Problem**: "failed to connect to temporal server"
**Solution**:
```bash
# Check Temporal server status
docker-compose logs temporal

# Temporal server takes ~30 seconds to fully start
```

### Worker Registration Issues

**Problem**: Workers not appearing in Temporal Web UI
**Solution**:
```bash
# Restart worker
docker-compose restart worker

# Check worker logs
docker-compose logs worker
```

### Workflow Timeouts

**Problem**: Workflows timing out before completion
**Solution**: The system is designed to complete within 15 seconds. If you're seeing timeouts:

1. Check the manual approval is sent within 10 seconds
2. Verify database connectivity
3. Check activity retry logs

### Import Errors

**Problem**: "ImportError: No module named 'temporalio'"
**Solution**:
```bash
# Ensure you're in the right environment and dependencies are installed
pip install -r requirements.txt
```

## Performance Testing

### Single Workflow Test

```bash
# Test basic functionality
make demo
```

### Concurrent Workflows

```bash
# Start multiple orders concurrently
for i in {1..5}; do
  curl -X POST "http://localhost:8000/orders/concurrent-$i/start" \
    -H "Content-Type: application/json" \
    -d "{\"payment_id\": \"pay-$i\", \"items\": [{\"sku\":\"TEST\",\"qty\":1}]}" &
done
wait

# Approve them all
for i in {1..5}; do
  curl -X POST "http://localhost:8000/orders/concurrent-$i/signals/approve" \
    -H "Content-Type: application/json" \
    -d '{"approved_by": "batch_test"}' &
done
wait
```

## Cleanup

```bash
# Stop services
make down

# Remove volumes and clean up
make clean
```

## Production Considerations

For production deployment, consider:

1. **Environment Variables**: Use proper secrets management
2. **Database**: Use managed PostgreSQL service
3. **Temporal**: Use Temporal Cloud or managed Temporal cluster
4. **Monitoring**: Add Prometheus/Grafana monitoring
5. **Logging**: Centralized log aggregation
6. **Security**: TLS, authentication, network policies
7. **Scaling**: Multiple worker instances, load balancing
8. **Backup**: Database backup strategy
9. **Disaster Recovery**: Multi-region deployment
