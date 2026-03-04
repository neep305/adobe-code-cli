# Adobe Experience Platform Web UI

Web interface for the Adobe Experience Platform CLI with full feature parity and real-time synchronization.

## Architecture

- **Backend**: FastAPI (Python 3.12+) - Reuses CLI business logic
- **Frontend**: Next.js 14+ with App Router (to be implemented)
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **UI Framework**: shadcn/ui with Tailwind CSS

## Features

### Implemented ✅
- **User authentication** (JWT-based registration and login)
- **Database models** for users, schemas, datasets, batches, dataflows
- **Health check** and version endpoints
- **Docker containerization** for all services (backend, frontend, PostgreSQL, Redis)
- **Batch management API** (create, status, upload, complete)
- **Dataflow monitoring API** (list, runs, health analysis with AI recommendations)
- **WebSocket real-time updates** (batch status with heartbeat)
- **Next.js 14 frontend** with App Router and TypeScript
- **Authentication UI** (login and registration pages)
- **Batch monitoring UI** with real-time updates (Slice 1 complete) ⭐
- **Dashboard layout** with navigation
- **shadcn/ui components** (Button, Card, Badge, Progress, Alert, Input, Label)

### In Progress 🚧
- Dataflow health dashboard UI (Slice 2 - backend APIs ready)
- Dataset management API and UI
- File upload progress WebSocket
- Background task for batch monitoring

### Planned 📋
- Schema management UI with browser and AI-powered generation
- Visual schema editor with field tree
- Interactive ERD diagrams
- Dataset creation wizard
- Advanced filtering and search
- Bulk operations support

## Quick Start

### Using Docker (Recommended)

1. **Set environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Adobe credentials
   ```

2. **Start services**:
   ```bash
   docker-compose up -d
   ```

3. **Check logs**:
   ```bash
   docker-compose logs -f backend
   ```

4. **Access services**:
   - **Frontend UI**: http://localhost:3000 ⭐
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

5. **Stop services**:
   ```bash
   docker-compose down
   ```

### Local Development

See [backend/README.md](./backend/README.md) for detailed setup instructions.

## Project Structure

```
web/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── config.py          # Settings
│   │   ├── auth/              # Authentication
│   │   ├── db/                # Database m (auth, batch, dataflow)
│   │   ├── websockets/        # WebSocket handlers
│   │   ├── schemas/           # Pydantic schemas
│   │   └── cache/             # Redis cache (planned)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── frontend/                   # Next.js 14 frontend ✅
│   ├── app/                   # App Router pages
│   │   ├── login/            # Authentication pages
│   │   ├── register/
│   │   └── batches/          # Batch monitoring (Slice 1)
│   ├── components/           # React components
│   │   ├── ui/               # shadcn/ui components
│   │   └── batch/            # Batch-specific components
│   ├── hooks/                # React Query hooks
│   ├── lib/                  # API client and utilities
│   ├── package.json
│   ├── Dockerfile
│   └── README.md
├── docker-compose.yml         # Docker orchestration
├── .env.example               # Environment template
├── QUICKSTART.md              # Quick start guidn
├── .env.example               # Environment template
└── README.md                  # This file
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user
- `GET /api/auth/status` - Check auth status

### Batch Management
- `POST /api/datasets/{dataset_id}/batches` - Create batch
- `GET /api/batches/{batch_id}` - Get batch status
- `POST /api/batches/{batch_id}/complete` - Complete batch
- `POST /api/batches/{batch_id}/files` - Upload file

### Dataflow Monitoring
- `GET /api/dataflows` - List dataflows
- `GET /api/dataflows/{flow_id}` - Get dataflow details
- `GET /api/dataflows/{flow_id}/runs` - List runs
- `GET /api/dataflows/{flow_id}/health` - Health analysis

### WebSocket (Real-time)
- `WS /ws/batch/{batch_id}/status` - Batch status updates

### Health
- `GET /api/health` - Health check
- `GET /api/version` - Version info

## CLI ↔ Web Synchronization

The Web UI and CLI share the same Adobe Experience Platform API as the single source of truth:

**CLI → Web**: 
- CLI operations directly hit Adobe API
- Web polls Adobe API and caches in PostgreSQL
- Web displays unified view of all resources

**Web → CLI**:
- Web operations hit Adobe API via backend
- CLI `list` commands fetch from Adobe API
- Automatic synchronization (no manual sync needed)

**Conflict Resolution**: Adobe API is the source of truth. Web database is a cache for metadata and progress tracking.

## Development Roadmap

### Phase 1: Backend API (Current)
- ✅ Authentication system
- ✅ Database models
- ✅ Docker setup
- 🚧 Schema management routes
- 🚧 Dataset management routes
- 🚧 Ingestion routes
- 🚧 Dataflow monitoring routes
- 🚧 WebSocket endpoints

### Phase 2: Frontend
- Next.js 14+ App Router setup
- shadcn/ui component integration
- Authentication flow (login/register)
- Schema list and create pages
- Dataset management UI
- File upload with progress

### Phase 3: Advanced Features
- AI-powered schema generation UI
- Visual schema editor
- Interactive ERD viewer (React Flow)
- Dataflow health dashboard
- Real-time batch monitoring
- AI chat assistant

### Phase 4: Production
- User management and RBAC
- Multi-tenant support
- Activity audit logs
- Scheduled ingestion jobs
- Performance optimization
- Security hardening

## Environment Variables

Required environment variables (copy from `.env.example`):

```bash
# Adobe Experience Platform
AEP_CLIENT_ID=your_client_id
AEP_CLIENT_SECRET=your_secret
AEP_ORG_ID=your_org@AdobeOrg
AEP_TECHNICAL_ACCOUNT_ID=your_account@techacct.adobe.com
AEP_SANDBOX_NAME=prod
AEP_TENANT_ID=_yourtenant

# AI Providers (Optional)
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# Security
SECRET_KEY=your-secret-key-min-32-chars
```

## Testing

### Backend API Testing

```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password123"

# Save the token from login response
TOKEN="your_access_token_here"

# Get user info (with token)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# List dataflows
curl http://localhost:8000/api/dataflows \
  -H "Authorization: Bearer $TOKEN"

# Get dataflow health
curl "http://localhost:8000/api/dataflows/{flow_id}/health?window_days=7" \
  -H "Authorization: Bearer $TOKEN"

# Create batch
curl -X POST http://localhost:8000/api/datasets/1/batches \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id":1,"format":"parquet"}'

# Get batch status
curl http://localhost:8000/api/batches/1 \
  -H "Authorization: Bearer $TOKEN"
```

### WebSocket Testing

```bash
# Install wscat for WebSocket testing
npm install -g wscat

# Connect to batch status WebSocket
wscat -c "ws://localhost:8000/ws/batch/1/status?token=$TOKEN"

# You should receive:
# {"event":"connected","batch_id":1,"message":"Connected to batch 1 status updates"}
# Periodic pings: {"event":"ping","timestamp":...}
```

## Contributing

1. Create feature branch from `main`
2. Implement changes in `web/backend/` or `web/frontend/`
3. Test locally with Docker Compose
4. Submit pull request

## License

See main project LICENSE file.

## Next Steps

See [backend/README.md](./backend/README.md) for backend development details.

Frontend implementation guide coming in Phase 2.
