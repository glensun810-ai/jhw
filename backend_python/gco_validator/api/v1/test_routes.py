"""
Test-related API routes for GEO Content Quality Validator
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import uuid
from datetime import datetime

from gco_validator.schemas.test_schemas import (
    BrandTestRequest, BrandTestResponse, 
    TestProgressResponse, TestHistoryResponse
)
from gco_validator.test_engine import TestExecutor, ExecutionStrategy
from gco_validator.ai_clients import AIAdapterFactory
from gco_validator.question_system import QuestionManager, TestCaseGenerator
from gco_validator.scoring import ResponseEvaluator
from gco_validator.reporting import ReportGenerator
from gco_validator.core.exceptions import ValidationError, TestExecutionException
from gco_validator.core.logging import api_logger, test_logger

router = APIRouter()

# In-memory store for execution progress (in production, use Redis or database)
execution_store = {}


@router.post("/brand-test", response_model=BrandTestResponse)
async def perform_brand_test(request: BrandTestRequest) -> BrandTestResponse:
    """
    Perform brand cognition test across multiple AI platforms
    """
    api_logger.info(f"Starting brand test for '{request.brand_name}' with {len(request.selected_models)} models")
    
    try:
        # Validate inputs
        if not request.brand_name:
            raise ValidationError("Brand name is required")
        
        if not request.selected_models:
            raise ValidationError("At least one AI model must be selected")
        
        # Initialize components
        question_manager = QuestionManager()
        test_case_generator = TestCaseGenerator()
        executor = TestExecutor(
            max_workers=request.max_workers or 5,
            strategy=ExecutionStrategy.CONCURRENT
        )
        evaluator = ResponseEvaluator()
        report_generator = ReportGenerator()
        
        # Validate and process questions
        if request.custom_questions:
            validation_result = question_manager.validate_custom_questions(request.custom_questions)
            if not validation_result['valid']:
                raise ValidationError(f"Invalid questions: {'; '.join(validation_result['errors'])}")
            
            questions = [q.replace('{brandName}', request.brand_name) for q in validation_result['cleaned_questions']]
        else:
            # Use default questions
            questions = [
                f"介绍一下{request.brand_name}",
                f"{request.brand_name}的主要产品是什么",
                f"{request.brand_name}和竞品有什么区别"
            ]
        
        # Generate test cases
        test_cases = test_case_generator.generate_test_cases(
            request.brand_name,
            request.selected_models,
            questions
        )
        
        api_logger.info(f"Generated {len(test_cases)} test cases for execution")
        
        # Execute tests with progress tracking
        execution_id = str(uuid.uuid4())
        
        def progress_callback(task_id, progress):
            # Update progress in the store
            execution_store[execution_id] = {
                'progress': progress.progress_percentage,
                'completed': progress.completed_tests,
                'total': progress.total_tests,
                'status': progress.status.value,
                'last_updated': datetime.now().isoformat()
            }
            test_logger.info(f"Execution {execution_id} progress: {progress.progress_percentage:.1f}%")
        
        # Execute the tests
        results = executor.execute_tests(
            test_cases, 
            request.api_key or "", 
            progress_callback
        )
        
        executor.shutdown()
        
        # Process results and calculate scores
        detailed_results = []
        for result in results['results']:
            if result.get('success'):
                ai_response_content = result['result']
                
                # Evaluate the response
                evaluation = evaluator.evaluate_response(
                    ai_response_content.get('content', ''),
                    result.get('question', ''),
                    request.brand_name
                )
                
                detailed_result = {
                    'ai_model': result.get('model', 'unknown'),
                    'question': result.get('question', ''),
                    'response': ai_response_content.get('content', ''),
                    'accuracy': evaluation.accuracy,
                    'completeness': evaluation.completeness,
                    'relevance': evaluation.relevance,
                    'coherence': evaluation.coherence,
                    'overall_score': evaluation.overall_score,
                    'tokens_used': ai_response_content.get('tokens_used', 0),
                    'latency': ai_response_content.get('latency', 0),
                    'category': 'domestic' if result.get('model', '') in [
                        '通义千问', '文心一言', '豆包', 'Kimi', '元宝', 'DeepSeek', '讯飞星火'
                    ] else 'international'
                }
            else:
                detailed_result = {
                    'ai_model': result.get('model', 'unknown'),
                    'question': result.get('question', ''),
                    'response': f"Error: {result.get('error', 'Unknown error')}",
                    'accuracy': 0,
                    'completeness': 0,
                    'relevance': 0,
                    'coherence': 0,
                    'overall_score': 0,
                    'tokens_used': 0,
                    'latency': 0,
                    'category': 'unknown'
                }
            detailed_results.append(detailed_result)
        
        # Calculate overall score
        successful_results = [r for r in detailed_results if r['overall_score'] > 0]
        if successful_results:
            total_score = sum(r['overall_score'] for r in successful_results)
            overall_score = round(total_score / len(successful_results)) if successful_results else 0
        else:
            overall_score = 0
        
        # Generate report
        ai_model_names = [model['name'] if isinstance(model, dict) else model for model in request.selected_models]
        report_data = report_generator.generate_report(
            brand_name=request.brand_name,
            ai_models=ai_model_names,
            overall_score=overall_score,
            detailed_results=detailed_results
        )
        
        api_logger.info(f"Brand test completed for '{request.brand_name}'. Overall score: {overall_score}")
        
        return BrandTestResponse(
            status='success',
            results=detailed_results,
            overall_score=overall_score,
            total_tests=len(detailed_results),
            execution_id=execution_id,
            report_summary=report_data.summary_stats
        )
        
    except ValidationError as e:
        api_logger.warning(f"Validation error in brand test: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except TestExecutionException as e:
        api_logger.error(f"Test execution error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        api_logger.error(f"Unexpected error in brand test: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/progress/{execution_id}", response_model=TestProgressResponse)
async def get_test_progress(execution_id: str) -> TestProgressResponse:
    """
    Get the progress of a test execution
    """
    api_logger.info(f"Getting progress for execution {execution_id}")
    
    if execution_id in execution_store:
        progress_data = execution_store[execution_id]
        return TestProgressResponse(
            execution_id=execution_id,
            progress=progress_data['progress'],
            completed=progress_data['completed'],
            total=progress_data['total'],
            status=progress_data['status']
        )
    else:
        # For backward compatibility, return a default response
        return TestProgressResponse(
            execution_id=execution_id,
            progress=0,
            completed=0,
            total=1,
            status="not_found"
        )


@router.get("/history", response_model=TestHistoryResponse)
async def get_test_history() -> TestHistoryResponse:
    """
    Get test execution history
    """
    api_logger.info("Getting test history")
    
    # In a real implementation, this would fetch from a database
    # For now, return a sample response
    return TestHistoryResponse(
        status='success',
        history=[],
        count=0
    )