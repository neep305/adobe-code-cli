"""Main FastAPI application for Adobe AEP Web UI."""

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
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"   Debug mode: {settings.debug}")
    print(f"   AEP Sandbox: {settings.aep_sandbox_name}")
    
    # Initialize database
    from app.db.database import init_db
    await init_db()
    print("   ✓ Database initialized")
    
    # TODO: Initialize Redis connection
    # TODO: Start background tasks (batch monitoring)
    
    yield
    
    # Shutdown
    print("🛑 Shutting down application")
    
    # Close database connections
    from app.db.database import close_db
    await close_db()
    print("   ✓ Database connections closed")
    
    # TODO: Close Redis connections
    # TODO: Cancel background tasks


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
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

# Include batch management router
from app.routers import batch
app.include_router(batch.router, prefix="/api", tags=["Batches"])

# Include dataflow monitoring router
from app.routers import dataflow
app.include_router(dataflow.router, prefix="/api/dataflows", tags=["Dataflows"])

# TODO: Include other routers
# from app.routers import dataset
# app.include_router(dataset.router, prefix="/api/datasets", tags=["Datasets"])

# Include WebSocket endpoints
from app.websockets import batch_status
app.add_websocket_route("/ws/batch/{batch_id}/status", batch_status.websocket_endpoint)

# TODO: Additional WebSocket endpoints
# from app.websockets import upload_progress
# app.add_websocket_route("/ws/upload/{upload_id}", upload_progress.websocket_endpoint)
# from app.websockets import batch_monitor, upload_progress
# app.add_websocket_route("/ws/batch/{batch_id}/status", batch_monitor.websocket_endpoint)
# app.add_websocket_route("/ws/upload/{upload_id}", upload_progress.websocket_endpoint)


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


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
