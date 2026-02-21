"""
Test case generator for AI platform testing
Creates test cases that can be executed in parallel
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum
import uuid
from datetime import datetime
from wechat_backend.logging_config import api_logger


class TestCaseStatus(Enum):
    """Status of a test case"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TestCase:
    """Represents a single test case for AI platform evaluation"""
    id: str
    brand_name: str
    ai_model: str
    question: str
    status: TestCaseStatus = TestCaseStatus.PENDING
    result: Dict[str, Any] = None
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    error_message: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def start_execution(self):
        """Mark the test case as running"""
        self.status = TestCaseStatus.RUNNING
        self.started_at = datetime.now()
        api_logger.info(f"Started executing test case {self.id} for model {self.ai_model}")
    
    def complete_execution(self, result: Dict[str, Any]):
        """Mark the test case as completed with results"""
        self.status = TestCaseStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
        api_logger.info(f"Completed test case {self.id} for model {self.ai_model}")
    
    def fail_execution(self, error_message: str):
        """Mark the test case as failed"""
        self.status = TestCaseStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()
        api_logger.error(f"Failed test case {self.id} for model {self.ai_model}: {error_message}")


class TestCaseGenerator:
    """Generates test cases for AI platform evaluation"""
    
    def __init__(self):
        api_logger.info("Initialized TestCaseGenerator")
    
    def generate_test_cases(
        self, 
        brand_name: str, 
        ai_models: List[Dict[str, str]], 
        questions: List[str]
    ) -> List[TestCase]:
        """
        Generate test cases for the given inputs
        
        Args:
            brand_name: Name of the brand to test
            ai_models: List of AI model dictionaries with 'name' field
            questions: List of questions to ask each AI model
            
        Returns:
            List of TestCase objects that can be executed in parallel
        """
        test_cases = []
        
        for model_info in ai_models:
            model_name = model_info.get('name', model_info) if isinstance(model_info, dict) else model_info
            
            for question in questions:
                test_case = TestCase(
                    id=str(uuid.uuid4()),
                    brand_name=brand_name,
                    ai_model=model_name,
                    question=question
                )
                test_cases.append(test_case)
        
        api_logger.info(f"Generated {len(test_cases)} test cases for brand '{brand_name}' across {len(ai_models)} models with {len(questions)} questions")
        return test_cases
    
    def generate_test_cases_from_templates(
        self,
        brand_name: str,
        ai_models: List[Dict[str, str]],
        question_manager,
        custom_questions: List[str] = None,
        use_default_questions: bool = True
    ) -> List[TestCase]:
        """
        Generate test cases using standard templates and optional custom questions
        
        Args:
            brand_name: Name of the brand to test
            ai_models: List of AI model dictionaries with 'name' field
            question_manager: QuestionManager instance to access templates
            custom_questions: Optional list of custom questions
            use_default_questions: Whether to include default questions
            
        Returns:
            List of TestCase objects
        """
        all_questions = []
        
        # Add custom questions if provided
        if custom_questions:
            validation_result = question_manager.validate_custom_questions(custom_questions)
            if not validation_result['valid']:
                raise ValueError(f"Invalid custom questions: {'; '.join(validation_result['errors'])}")
            all_questions.extend(validation_result['cleaned_questions'])
        
        # Add default questions if requested
        if use_default_questions and not all_questions:
            # Use default questions if no custom questions provided
            default_questions = [
                f"介绍一下{brand_name}",
                f"{brand_name}的主要产品是什么",
                f"{brand_name}和竞品有什么区别"
            ]
            all_questions.extend(default_questions)
        
        # Generate test cases
        test_cases = self.generate_test_cases(brand_name, ai_models, all_questions)
        
        api_logger.info(f"Generated {len(test_cases)} test cases from templates and custom questions for brand '{brand_name}'")
        return test_cases
    
    def execute_test_cases_sequentially(
        self,
        test_cases: List[TestCase],
        ai_client_factory
    ) -> List[TestCase]:
        """
        Execute test cases sequentially (for simpler implementation)
        
        Args:
            test_cases: List of test cases to execute
            ai_client_factory: Factory to create AI clients
            
        Returns:
            List of completed test cases
        """
        results = []
        
        for test_case in test_cases:
            try:
                test_case.start_execution()
                
                # Create AI client for this model
                ai_client = ai_client_factory.create(test_case.ai_model, "", test_case.ai_model)
                
                # Send the question to the AI
                ai_response = ai_client.send_prompt(
                    f"Please answer the following question about {test_case.brand_name}: {test_case.question}"
                )
                
                # Format the result
                result = {
                    'question': test_case.question,
                    'answer': ai_response.content,
                    'model': ai_response.model,
                    'platform': ai_response.platform,
                    'tokens_used': ai_response.tokens_used,
                    'latency': ai_response.latency,
                    'success': ai_response.success
                }
                
                test_case.complete_execution(result)
                
            except Exception as e:
                test_case.fail_execution(str(e))
            
            results.append(test_case)
        
        return results