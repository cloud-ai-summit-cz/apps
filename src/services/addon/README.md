# Add-On Service

Add-On Order Service for Stuffed Toy World Tour - handles ordering and fulfillment of accessories/experiences for trips.

## Overview

The Add-On Service provides REST APIs for creating and managing add-on orders, with async fulfillment via Azure Service Bus and integration with Demo Media and Trip services.

## Architecture

- **API**: FastAPI REST endpoints for order management
- **Worker**: Service Bus consumer for fulfillment processing
- **Storage**: Cosmos DB (HPK: ownerId/tripId) for orders, Azure Blob Storage for fulfillment images
- **Messaging**: Azure Service Bus queue `addon-fulfill`

## Features

- ✅ Create add-on orders with idempotency support
- ✅ Owner-scoped order access via JWT authentication
- ✅ Async fulfillment workflow (pending → in_progress → fulfilled/failed)
- ✅ Integration with Demo Media for image generation
- ✅ Integration with Trip Service for gallery updates
- ✅ OpenTelemetry instrumentation (traces, metrics, logs)
- ✅ KEDA autoscaling for worker pods

## Prerequisites

- Python 3.12+
- uv (package manager)
- Azure credentials configured
- Access to:
  - Cosmos DB (database: `toytripdb`, container: `addons`)
  - Service Bus (queue: `addon-fulfill`)
  - Azure Storage (container: `fulfillment`)
  - Trip Service
  - Toy Service
  - Demo Media Service

## Local Development

### Setup

```bash
# Install dependencies
cd src/services/addon
uv pip install -e .

# Copy and configure environment
cp .env.example .env
# Edit .env with your values
```

### Run API

```bash
# Start the API server
python main.py

# Or with uvicorn
uvicorn main:app --reload --port 8003
```

### Run Worker

```bash
# Start the fulfillment worker
python workers/fulfillment_worker.py
```

### API Endpoints

- `POST /addon/trips/{trip_id}/addons` - Create addon order (requires `Idempotency-Key` header)
- `GET /addon/trips/{trip_id}/addons` - List orders for a trip
- `GET /addon/addons/{order_id}?trip_id={trip_id}` - Get single order
- `GET /health` - Health check

### Example Usage

```bash
# Create an add-on order
curl -X POST http://localhost:8003/addon/trips/{trip_id}/addons \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: unique-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "addon_type": "beret",
    "notes": "Make it red"
  }'

# List orders for a trip
curl http://localhost:8003/addon/trips/{trip_id}/addons \
  -H "Authorization: Bearer <token>"

# Get a specific order
curl http://localhost:8003/addon/addons/{order_id}?trip_id={trip_id} \
  -H "Authorization: Bearer <token>"
```

## Testing

```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## Deployment

### Docker Build

```bash
# Build API image
docker build -t addon-service:latest .

# Build worker image
docker build -t addon-worker:latest --build-arg CMD="python workers/fulfillment_worker.py" .
```

### Kubernetes Deployment

See `helm-charts/addon/` for Helm chart configuration.

```bash
# Deploy with Helm
helm upgrade --install addon ./helm-charts/addon \
  --namespace default \
  --values ./helm-charts/addon/values.yaml
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `COSMOS_ENDPOINT` | Cosmos DB endpoint | Required |
| `COSMOS_CONTAINER_NAME` | Container name | `addons` |
| `SERVICE_BUS_NAMESPACE` | Service Bus namespace | Required |
| `SERVICE_BUS_QUEUE_NAME` | Queue name | `addon-fulfill` |
| `TRIP_SERVICE_URL` | Trip Service URL | `http://localhost:8002` |
| `DEMO_MEDIA_SERVICE_URL` | Demo Media URL | `http://localhost:8005` |
| `API_PORT` | API server port | `8003` |

## Observability

### Metrics

- `addons_ordered_total` - Counter for orders created (labels: addon_type, status)
- `addon_fulfillment_duration_seconds` - Histogram for fulfillment duration
- `addon_fulfillment_processed_total` - Counter for processed fulfillments
- `addon_worker_retries_total` - Counter for worker retries

### Logs

Structured logs with fields:
- `owner_id` - Owner OID
- `trip_id` - Trip UUID
- `order_id` - Order ID
- `addon_type` - Type of addon
- `status` - Order status

### Traces

Spans:
- `addon.order.create` - Order creation
- `addon.fulfill` - Fulfillment processing

## Security

- JWT authentication on all endpoints
- Owner-scoped access (validated via Trip/Toy ownership)
- Managed Identity for Azure services
- No public blob URLs
- Idempotency keys for duplicate prevention

## Troubleshooting

### Common Issues

1. **Connection refused to Cosmos DB**
   - Verify `COSMOS_ENDPOINT` is correct
   - Check managed identity has appropriate RBAC roles

2. **Service Bus queue not found**
   - Ensure queue `addon-fulfill` exists
   - Verify `SERVICE_BUS_NAMESPACE` format

3. **Demo Media service unavailable**
   - Check `DEMO_MEDIA_SERVICE_URL` is reachable
   - Worker will retry with backoff

4. **Order stuck in pending**
   - Check worker logs for errors
   - Verify Service Bus queue is being consumed

## License

See repository LICENSE file.
