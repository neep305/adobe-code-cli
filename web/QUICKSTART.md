# Adobe AEP Web UI - Quick Start

Before running web services, install the CLI and set up your environment via [../docs/install.md](../docs/install.md).

## Start Development Environment

From the `web/` directory, run:

```bash
# Start all services (backend + frontend + databases)
docker-compose up

# Or start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## First Time Setup

1. **Set Adobe Credentials** in `.env` or environment variables:
```bash
export AEP_CLIENT_ID="your-client-id"
export AEP_CLIENT_SECRET="your-client-secret"
export AEP_ORG_ID="your-org-id"
export AEP_TECHNICAL_ACCOUNT_ID="your-technical-account-id"
export AEP_SANDBOX_NAME="prod"
export AEP_TENANT_ID="your-tenant-id"
```

2. **Install Frontend Dependencies** (first time only):
```bash
cd frontend
npm install
cd ..
```

3. **Create `.env.local` for frontend**:
```bash
cd frontend
cp .env.local.example .env.local
```

4. **Start services**:
```bash
docker-compose up
```

## Usage

### Register a new user:
1. Open http://localhost:3000
2. You'll be redirected to login page
3. Click "Sign up" to create an account
4. After registration, you'll be redirected to the batches page

### Monitor Batches:
1. Navigate to "Batches" in the top menu
2. Click on any batch to see detailed status
3. Real-time updates via WebSocket (look for "Live Updates" badge)

## Development

### Frontend Only (with hot reload):
```bash
cd frontend
npm run dev
```

### Backend Only:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Stop All Services:
```bash
docker-compose down

# Remove volumes (clears database)
docker-compose down -v
```

## Troubleshooting

### Frontend Not Building:
- Ensure Node.js 20+ is installed
- Run `npm install` in `frontend/` directory
- Check `docker-compose logs frontend` for errors

### Backend Not Starting:
- Check Adobe credentials are set
- Verify PostgreSQL is healthy: `docker-compose ps`
- Check logs: `docker-compose logs backend`

### Database Connection Issues:
- Wait for health checks to pass
- Check PostgreSQL logs: `docker-compose logs postgres`
- Verify DATABASE_URL is correct

### WebSocket Not Connecting:
- Check backend is accessible at http://localhost:8000
- Verify JWT token is valid (check browser console)
- Try refreshing the page
- System falls back to polling automatically

## Next Steps

See individual README files:
- [Frontend README](frontend/README.md) - Frontend development details
- [Backend README](backend/README.md) - Backend API documentation
