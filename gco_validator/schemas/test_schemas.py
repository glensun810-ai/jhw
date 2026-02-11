"""
Request/Response schemas for GEO Content Quality Validator
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class AIModel(BaseModel):
    """Schema for AI model configuration"""
    name: str = Field(..., description="Name of the AI model")
    checked: bool = Field(True, description="Whether this model is selected")


class BrandTestRequest(BaseModel):
    """Request schema for brand test endpoint"""
    brand_name: str = Field(..., description="Name of the brand to test", min_length=1, max_length=100)
    selected_models: List[AIModel] = Field(..., description="List of selected AI models", min_items=1)
    custom_questions: List[str] = Field([], description="Custom questions to ask", max_items=5)
    api_key: Optional[str] = Field(None, description="API key for AI platforms")
    max_workers: Optional[int] = Field(5, description="Maximum number of concurrent workers", ge=1, le=20)


class TestResult(BaseModel):
    """Schema for individual test result"""
    ai_model: str = Field(..., description="AI model that generated the response")
    question: str = Field(..., description="Question that was asked")
    response: str = Field(..., description="Response from the AI model")
    accuracy: float = Field(..., description="Accuracy score (0-100)", ge=0, le=100)
    completeness: float = Field(..., description="Completeness score (0-100)", ge=0, le=100)
    relevance: float = Field(..., description="Relevance score (0-100)", ge=0, le=100)
    coherence: float = Field(..., description="Coherence score (0-100)", ge=0, le=100)
    overall_score: float = Field(..., description="Overall quality score (0-100)", ge=0, le=100)
    tokens_used: int = Field(..., description="Number of tokens used")
    latency: float = Field(..., description="Response time in seconds")
    category: str = Field(..., description="Category of the AI model (domestic/international)")


class BrandTestResponse(BaseModel):
    """Response schema for brand test endpoint"""
    status: str = Field(..., description="Status of the test execution")
    results: List[TestResult] = Field(..., description="List of test results")
    overall_score: float = Field(..., description="Overall score for the brand test", ge=0, le=100)
    total_tests: int = Field(..., description="Total number of tests performed")
    execution_id: str = Field(..., description="ID of the test execution")
    report_summary: Dict[str, Any] = Field(..., description="Summary statistics for the report")


class TestProgressResponse(BaseModel):
    """Response schema for test progress endpoint"""
    execution_id: str = Field(..., description="ID of the test execution")
    progress: float = Field(..., description="Progress percentage (0-100)", ge=0, le=100)
    completed: int = Field(..., description="Number of completed tests")
    total: int = Field(..., description="Total number of tests")
    status: str = Field(..., description="Current status of the execution")


class TestHistoryResponse(BaseModel):
    """Response schema for test history endpoint"""
    status: str = Field(..., description="Status of the request")
    history: List[Dict[str, Any]] = Field(..., description="List of historical test records")
    count: int = Field(..., description="Total count of historical records")


class AIPlatform(BaseModel):
    """Schema for AI platform information"""
    name: str = Field(..., description="Name of the AI platform")
    checked: bool = Field(False, description="Whether this platform is selected by default")


class AIPlatformsResponse(BaseModel):
    """Response schema for AI platforms endpoint"""
    domestic: List[AIPlatform] = Field(..., description="List of domestic AI platforms")
    overseas: List[AIPlatform] = Field(..., description="List of overseas AI platforms")