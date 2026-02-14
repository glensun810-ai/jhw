"""
Unified exception handling for the GEO Content Quality Validator
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class GCOValidatorException(Exception):
    """Base exception class for the GEO Content Quality Validator"""
    def __init__(self, message: str, status_code: int = 500, detail: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class ValidationError(GCOValidatorException):
    """Raised when input validation fails"""
    def __init__(self, message: str, detail: Any = None):
        super().__init__(message, 422, detail)


class AIPlatformException(GCOValidatorException):
    """Raised when AI platform operations fail"""
    def __init__(self, message: str, detail: Any = None):
        super().__init__(message, 502, detail)


class TestExecutionException(GCOValidatorException):
    """Raised when test execution fails"""
    def __init__(self, message: str, detail: Any = None):
        super().__init__(message, 500, detail)


def add_exception_handlers(app: FastAPI):
    """Add exception handlers to the FastAPI application"""
    
    @app.exception_handler(GCOValidatorException)
    async def handle_gco_validator_exception(request: Request, exc: GCOValidatorException):
        logger.error(f"GCOValidatorException: {exc.message}", exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "detail": exc.detail
                }
            }
        )
    
    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError):
        logger.warning(f"ValidationError: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "detail": exc.detail
                }
            }
        )
    
    @app.exception_handler(AIPlatformException)
    async def handle_ai_platform_error(request: Request, exc: AIPlatformException):
        logger.error(f"AIPlatformException: {exc.message}", exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "detail": exc.detail
                }
            }
        )
    
    @app.exception_handler(TestExecutionException)
    async def handle_test_execution_error(request: Request, exc: TestExecutionException):
        logger.error(f"TestExecutionException: {exc.message}", exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "detail": exc.detail
                }
            }
        )
    
    # Handle generic exceptions
    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred"
                }
            }
        )


# Predefined logger instances for different modules
app_logger = logging.getLogger('gco_validator')
api_logger = logging.getLogger('gco_validator.api')
ai_logger = logging.getLogger('gco_validator.ai_clients')
test_logger = logging.getLogger('gco_validator.test_engine')
scoring_logger = logging.getLogger('gco_validator.scoring')
reporting_logger = logging.getLogger('gco_validator.reporting')