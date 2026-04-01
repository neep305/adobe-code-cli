"""Main FastAPI application for Adobe AEP Web UI."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"   Mode: {settings.web_mode}")
    print(f"   Debug mode: {settings.debug}")
    print(f"   AEP Sandbox: {settings.aep_sandbox_name}")
    
    # Initialize database
    from app.db.database import init_db
    await init_db()
    print("   [OK] Database initialized")
    
    # Initialize cache based on mode
    from app.cache import init_cache
    if settings.cache_backend == "memory":
        init_cache(backend="memory", maxsize=1000, default_ttl=300)
        print("   [OK] Memory cache initialized")
    elif settings.cache_backend == "disk":
        init_cache(backend="disk")
        print("   [OK] Disk cache initialized")
    else:
        # Redis mode (docker/dev)
        print("   [WARNING] Redis initialization not yet implemented")
    
    # Start batch monitoring background task
    from app.tasks.batch_monitor import run_batch_monitor
    monitor_task = asyncio.create_task(run_batch_monitor())
    print("   [OK] Batch monitor background task started")
    
    yield
    
    # Cancel background tasks on shutdown
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    print("   [OK] Background tasks stopped")
    
    # Shutdown
    print("Shutting down application")
    
    # Close cache
    from app.cache import close_cache
    await close_cache()
    print("   [OK] Cache closed")
    
    # Close database connections
    from app.db.database import close_db
    await close_db()
    print("   [OK] Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Web UI backend for Adobe Experience Platform CLI integration",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/api/version")
async def version() -> dict:
    """Get application version information."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
    }


# Include authentication router
from app.routers import auth
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])

# Include batch management router
from app.routers import batch
app.include_router(batch.router, prefix="/api", tags=["Batches"])

# Include dataflow monitoring router
from app.routers import dataflow
app.include_router(dataflow.router, prefix="/api/dataflows", tags=["Dataflows"])

# Include analyze router
from app.routers import analyze
app.include_router(analyze.router, prefix="/api/analyze", tags=["Analyze"])

# Include dataset router
from app.routers import dataset
app.include_router(dataset.router, prefix="/api/datasets", tags=["Datasets"])

# Include schema router
from app.routers import schema
app.include_router(schema.router, prefix="/api/schemas", tags=["Schemas"])

# Include user settings router
from app.routers import settings as settings_router
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])

# Include WebSocket endpoints
from app.websockets import batch_status
app.add_api_websocket_route("/ws/batch/{batch_id}/status", batch_status.websocket_endpoint)

# Upload progress WebSocket endpoint
from app.websockets import upload_progress
app.add_api_websocket_route("/ws/upload/{upload_id}", upload_progress.websocket_endpoint)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "An error occurred",
        },
    )


# Serve static frontend files in standalone mode
if settings.web_mode == "standalone":
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    
    # Try multiple possible frontend build locations
    possible_paths = [
        Path(__file__).parent.parent.parent / "frontend" / "out",  # Development
        Path(__file__).parent / "frontend" / "out",  # Packaged in backend
        Path(__file__).parent.parent / "frontend" / "out",  # Alternative structure
    ]
    
    frontend_dist = None
    for path in possible_paths:
        if path.exists() and path.is_dir():
            frontend_dist = path
            break
    
    if frontend_dist:
        print(f"   [OK] Serving static frontend from: {frontend_dist}")
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    else:
        print(f"   [WARNING] Frontend build not found. Run 'cd web/frontend && npm run export'")
        print(f"     Searched paths: {[str(p) for p in possible_paths]}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
