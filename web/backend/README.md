# Adobe AEP Web UI - Backend

FastAPI-based backend server for the Adobe Experience Platform Web UI. Provides REST API and WebSocket endpoints that reuse the existing CLI business logic.

## Architecture

- **Framework**: FastAPI (async)
- **Database**: PostgreSQL 15+ with SQLAlchemy 2.0 (async)
- **Cache**: Redis 7+
- **Authentication**: JWT tokens with OAuth2
- **Real-time**: WebSocket for batch monitoring and upload progress

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Settings and configuration
│   ├── auth/                # Authentication (JWT, password hashing)
│   │   ├── dependencies.py  # Auth dependencies (get_current_user)
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── security.py      # JWT and password utilities
│   │   └── __init__.py
│   ├── db/                  # Database
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── database.py      # DB connection and session
│   │   └── __init__.py
│   ├── routers/             # API routers
│   │   ├── auth.py          # /api/auth endpoints
│   │   └── __init__.py
│   ├── websockets/          # WebSocket handlers
│   │   └── __init__.py
│   └── cache/               # Redis caching
│       └── __init__.py
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
└── README.md
```

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Adobe Experience Platform credentials

### Installation

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   
   # Install the CLI package in development mode
   pip install -e ../..
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Set up database**:
   ```bash
   # Create PostgreSQL database
   createdb aep_web
   
   # Or using psql:
   psql -U postgres
   CREATE DATABASE aep_web;
   CREATE USER aep_user WITH PASSWORD 'aep_password';
   GRANT ALL PRIVILEGES ON DATABASE aep_web TO aep_user;
   ```

5. **Initialize database tables**:
   Tables are automatically created on first startup via the lifespan event.

### Running

**Development mode** (with auto-reload):
```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode**:
```bash
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Documentation

When running in debug mode, API docs are available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (get access token)
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/status` - Check authentication status

### Batch Management

- `POST /api/datasets/{dataset_id}/batches` - Create new batch for ingestion
- `GET /api/batches/{batch_id}` - Get batch status and metrics
- `POST /api/batches/{batch_id}/complete` - Complete or abort batch
- `POST /api/batches/{batch_id}/files` - Upload file to batch

### Dataflow Monitoring

- `GET /api/dataflows` - List dataflows with filters
- `GET /api/dataflows/{flow_id}` - Get dataflow details
- `GET /api/dataflows/{flow_id}/runs` - List dataflow execution runs
- `GET /api/dataflows/{flow_id}/health` - Get dataflow health analysis

### WebSocket Endpoints

- `WS /ws/batch/{batch_id}/status` - Real-time batch status updates
  - Events: `connected`, `status_update`, `ping/pong`
  - Authentication: Via `token` query parameter

### Health Check

- `GET /api/health` - Health check
- `GET /api/version` - Version information

## Environment Variables

See [.env.example](./.env.example) for all available configuration options.

**Critical settings**:
- `SECRET_KEY`: JWT signing key (min 32 characters, change in production!)
- `DATABASE_URL`: PostgreSQL connection string
- `AEP_CLIENT_ID`, `AEP_CLIENT_SECRET`: Adobe credentials

## Database Models

- **User**: User accounts with email, hashed password, role
- **AEPConfig**: Adobe Experience Platform credentials per user
- **Schema**: XDM schema metadata
- **Dataset**: Dataset metadata
- **Batch**: Ingestion batch tracking
- **OnboardingProgress**: Tutorial progress

## Authentication Flow

1. User registers via `POST /api/auth/register`
2. User logs in via `POST /api/auth/login` → receives JWT token
3. User includes token in `Authorization: Bearer <token>` header
4. Backend validates token and loads user from database
5. Protected endpoints use `Depends(get_current_user)`

## Development

### Adding New Routes

1. Create router file in `app/routers/`
2. Define Pydantic schemas for request/response
3. Import and register in `app/main.py`:
   ```python
   from app.routers import myrouter
   app.include_router(myrouter.router, prefix="/api/myrouter", tags=["MyRouter"])
   ```

### Reusing CLI Logic

The backend reuses CLI service clients:
```python
from adobe_experience.aep.client import AEPClient
from adobe_experience.schema.xdm import XDMSchemaRegistry

async with AEPClient(config) as client:
    registry = XDMSchemaRegistry(client)
    schemas = await registry.list_schemas()
```

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

## Docker

See [../docker-compose.yml](../docker-compose.yml) for container setup.

## Next Steps

- [x] Implement batch management routes (`/api/batches`)
- [x] Implement dataflow monitoring routes (`/api/dataflows`)
- [x] Add WebSocket endpoint for real-time batch status
- [ ] Implement dataset management routes (`/api/datasets`)
- [ ] Implement schema management routes (`/api/schemas`)
- [ ] Add Redis caching layer for AEP tokens
- [ ] Add background task for automatic batch status polling
- [ ] Add upload progress WebSocket endpoint
- [ ] Add comprehensive error handling middleware
- [ ] Add request validation and rate limiting
- [ ] Add structured logging (JSON format)
- [ ] Add Prometheus metrics endpoint
- [ ] Add unit and integration tests

## License

See main project LICENSE.
