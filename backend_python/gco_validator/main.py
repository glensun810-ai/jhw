"""
GEO Content Quality Validator - Main Application Entry Point

This is the main FastAPI application that orchestrates all components
of the GEO Content Quality Validator system.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import logging.config

from gco_validator.core.config import settings
from gco_validator.api.v1.api import api_router
from gco_validator.core.logging import setup_logging
from gco_validator.core.exceptions import add_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    setup_logging()
    logging.info("Application starting up...")
    
    yield  # This is where the application runs
    
    # Shutdown
    logging.info("Application shutting down...")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="GEO Content Quality Validator API",
    description="API for validating content quality across AI platforms for GEO (Generative Engine Optimization)",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix="/api/v1")

# Add exception handlers
add_exception_handlers(app)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "GEO Content Quality Validator API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )