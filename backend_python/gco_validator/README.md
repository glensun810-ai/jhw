# GEO Content Quality Validator

A comprehensive system for validating content quality across AI platforms for GEO (Generative Engine Optimization).

## Project Structure

```
gco_validator/
├── main.py                 # Application entry point
├── requirements.txt        # Project dependencies
├── README.md             # This file
├── .env.example          # Environment variables example
├── api/                  # API endpoints
│   └── v1/               # Version 1 API
│       ├── __init__.py
│       ├── api.py        # Main API router
│       ├── test_routes.py    # Test-related endpoints
│       ├── ai_platform_routes.py  # AI platform endpoints
│       └── report_routes.py  # Report endpoints
├── models/               # Database models
│   ├── __init__.py
│   └── test_models.py    # Test-related database models
├── schemas/              # Pydantic schemas
│   ├── __init__.py
│   └── test_schemas.py   # Request/response schemas
├── ai_clients/           # AI platform clients
│   ├── __init__.py
│   ├── base.py           # Base AI client interface
│   ├── factory.py        # AI client factory
│   ├── deepseek_adapter.py  # DeepSeek adapter
│   └── ...               # Other AI platform adapters
├── test_engine/          # Test execution engine
│   ├── __init__.py
│   ├── scheduler.py      # Test scheduling logic
│   ├── progress_tracker.py  # Progress tracking
│   └── executor.py       # Test execution coordinator
├── scoring/              # Response scoring
│   ├── __init__.py
│   ├── evaluator.py      # Response evaluation logic
│   └── metrics.py        # Scoring metrics
├── reporting/            # Report generation
│   ├── __init__.py
│   ├── report_generator.py  # Report generation logic
│   └── visualizer.py     # Result visualization
├── database/             # Database utilities
│   ├── __init__.py
│   └── session.py        # Database session management
├── utils/                # Utility functions
│   ├── __init__.py
│   └── helpers.py        # Helper functions
├── core/                 # Core functionality
│   ├── __init__.py
│   ├── config.py         # Configuration management
│   ├── logging.py        # Logging configuration
│   └── exceptions.py     # Exception handling
├── config/               # Configuration files
│   ├── __init__.py
│   └── settings.py       # Application settings
└── tests/                # Test files
    ├── __init__.py
    ├── conftest.py       # Test configuration
    └── test_api.py       # API tests
```

## Core Modules

### 1. ai_clients
Handles connections to various AI platforms with standardized interfaces.
- `AIClient`: Base class defining the interface for all AI platform adapters
- `AIAdapterFactory`: Factory for creating AI client instances
- Platform-specific adapters (DeepSeek, ChatGPT, Claude, etc.)

### 2. test_engine
Manages test execution, scheduling, and progress tracking.
- `TestScheduler`: Handles scheduling of tests with different execution strategies
- `ProgressTracker`: Tracks progress of test executions
- `TestExecutor`: Coordinates test execution with progress tracking

### 3. scoring
Evaluates and scores AI responses based on quality metrics.
- `ResponseEvaluator`: Evaluates responses for accuracy, completeness, etc.
- `ScoringResult`: Data structure for scoring results
- Various metric calculation functions

### 4. reporting
Generates and formats test reports in various formats.
- `ReportGenerator`: Generates reports in JSON, CSV, HTML, and text formats
- `ResultVisualizer`: Provides visualization capabilities for test results

## Features

- **Modular Architecture**: Clean separation of concerns with dedicated modules
- **FastAPI Framework**: Modern, fast web framework with automatic API documentation
- **Standardized AI Interfaces**: Consistent interface across different AI platforms
- **Concurrent Test Execution**: Efficient execution of multiple tests simultaneously
- **Real-time Progress Tracking**: Monitor test execution progress
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Unified Exception Handling**: Consistent error handling across the application
- **Multiple Report Formats**: Export results in JSON, CSV, HTML, or text formats

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables (copy `.env.example` to `.env` and configure)

3. Run the application:
   ```bash
   uvicorn gco_validator.main:app --reload
   ```

## API Documentation

After starting the server, visit `http://localhost:8000/docs` for interactive API documentation.