# Story Service

AI-powered story generation service for the Stuffed Toy World Tour application.

## Overview

The Story service generates daily narrative recaps for trips using context from Trip, Toy, and Geo services, powered by Azure OpenAI.

## Architecture

- **API**: REST endpoints for story generation and retrieval
- **Worker**: Service Bus queue consumer for async story generation
- **Data**: Cosmos DB container `stories` with hierarchical partition key (ownerId, tripId)
- **AI**: Azure OpenAI (gpt-4o-mini) for text generation

## Features

- **Story Generation**: Generate AI-powered daily story recaps
- **Story Retrieval**: List and fetch stories for trips
- **Async Processing**: Queue-based story generation via Service Bus
- **Idempotency**: Prevent duplicate story generation
- **Observability**: OpenTelemetry tracing and metrics

## API Endpoints

### Generate Story
```
POST /api/stories/{tripId}/generate
```
Trigger story generation for a specific date (defaults to today).

Request body:
```json
{
  "story_date": "2025-12-07"
}
```

### List Stories
```
GET /api/stories/{tripId}
```
List all stories for a trip.

### Get Story
```
GET /api/stories/{tripId}/{storyId}
```
Fetch a specific story.

## Local Development

### Prerequisites

- Python 3.12+
- uv (package manager)
- Azure Cosmos DB account or emulator
- Azure OpenAI deployment
- Azure Service Bus namespace (for worker mode)

### Setup

1. Install dependencies:
```bash
uv pip install -e .
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

3. Run the API service:
```bash
python main.py
```

4. Run the worker (in separate terminal):
```bash
WORKER_MODE=true python workers/story_worker.py
```

### Testing

Run unit tests:
```bash
pytest
```

## Deployment

### Docker Build
```bash
docker build -t story-service:latest .
```

### Helm Chart
See `helm-charts/story/` for Kubernetes deployment configuration.

### Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `COSMOS_ENDPOINT`: Cosmos DB endpoint
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `SERVICE_BUS_NAMESPACE`: Service Bus namespace (for worker)
- `TRIP_SERVICE_URL`: Trip service URL
- `TOY_SERVICE_URL`: Toy service URL

## Observability

### Metrics
- `story_compositions_requested_total`: Total story generation requests
- `stories_viewed_total`: Total story views
- `story_generation_duration_seconds`: Generation latency
- `story_jobs_pending`: Pending queue jobs

### Logs
Structured JSON logs with fields:
- `owner_id`
- `trip_id`
- `story_id`
- `story_date`

### Traces
OpenTelemetry traces for:
- Story generation flow
- OpenAI API calls
- Cosmos DB operations

## References

- [Architecture](../../../specs/services/story/ARCHITECTURE.md)
- [Data Models](../../../specs/services/story/DATA_MODELS.md)
- [Security](../../../specs/services/story/SECURITY.md)
- [Observability](../../../specs/services/story/OBSERVABILITY.md)
- [Deployment](../../../specs/services/story/DEPLOYMENT.md)
- [Testing](../../../specs/services/story/TESTING.md)
- [Runbooks](../../../specs/services/story/RUNBOOKS.md)
