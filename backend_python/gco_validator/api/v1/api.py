"""
API Package for GEO Content Quality Validator
Version 1 API endpoints
"""
from fastapi import APIRouter

from . import test_routes, ai_platform_routes, report_routes

api_router = APIRouter()

# Include all route modules
api_router.include_router(test_routes.router, prefix="/tests", tags=["tests"])
api_router.include_router(ai_platform_routes.router, prefix="/ai-platforms", tags=["ai-platforms"])
api_router.include_router(report_routes.router, prefix="/reports", tags=["reports"])

__all__ = ["api_router"]