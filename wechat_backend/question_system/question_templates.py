"""
Question templates and management system
Defines standard question templates and custom question handling
"""
from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass
import re
import uuid
from ..logging_config import db_logger


class QuestionCategory(Enum):
    """Categories of questions for brand cognition testing"""
    BRAND_COGNITION = "brand_cognition"  # Who/What/Why questions about the brand
    PRODUCT_SERVICE = "product_service"  # Questions about products/services
    SCENARIO_UNDERSTANDING = "scenario_understanding"  # Scenario-based questions
    COMPARISON = "comparison"  # Comparison with competitors
    CUSTOM = "custom"  # User-defined custom questions


@dataclass
class QuestionTemplate:
    """Represents a question template with category and content"""
    id: str
    category: QuestionCategory
    template: str  # Template with placeholders like {brand_name}
    description: str
    difficulty: str = "medium"  # easy, medium, hard
    is_active: bool = True


@dataclass
class CustomQuestion:
    """Represents a custom question provided by the user"""
    id: str
    content: str
    category: QuestionCategory = QuestionCategory.CUSTOM
    original_content: Optional[str] = None  # Original content before cleaning


class QuestionManager:
    """Manages standard question templates and custom questions"""
    
    def __init__(self):
        """Initialize with standard question templates"""
        self.standard_templates = self._load_standard_templates()
    
    def _load_standard_templates(self) -> List[QuestionTemplate]:
        """Load standard question templates for brand cognition testing"""
        templates = [
            # Brand Cognition Questions (Who/What/Why)
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.BRAND_COGNITION,
                template="请介绍一下{brand_name}这个品牌。",
                description="General introduction of the brand",
                difficulty="easy"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.BRAND_COGNITION,
                template="什么是{brand_name}？",
                description="Basic identification of the brand",
                difficulty="easy"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.BRAND_COGNITION,
                template="为什么{brand_name}在市场中很重要？",
                description="Importance and significance of the brand",
                difficulty="hard"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.BRAND_COGNITION,
                template="{brand_name}的品牌定位是什么？",
                description="Brand positioning question",
                difficulty="medium"
            ),
            
            # Product/Service Understanding Questions
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.PRODUCT_SERVICE,
                template="{brand_name}的主要产品或服务是什么？",
                description="Main products or services offered",
                difficulty="easy"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.PRODUCT_SERVICE,
                template="请详细描述{brand_name}的核心产品功能。",
                description="Detailed product functionality",
                difficulty="medium"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.PRODUCT_SERVICE,
                template="{brand_name}的产品解决了什么具体问题？",
                description="Problem-solving aspect of products",
                difficulty="medium"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.PRODUCT_SERVICE,
                template="如何使用{brand_name}的服务？",
                description="Service usage instructions",
                difficulty="medium"
            ),
            
            # Scenario Understanding Questions
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.SCENARIO_UNDERSTANDING,
                template="如果我想使用{brand_name}解决XX问题，应该如何操作？",
                description="Scenario-based usage question",
                difficulty="medium"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.SCENARIO_UNDERSTANDING,
                template="在YY场景下，{brand_name}如何发挥作用？",
                description="Context-specific functionality",
                difficulty="hard"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.SCENARIO_UNDERSTANDING,
                template="假设我是ZZ类型的用户，{brand_name}适合我吗？",
                description="User-type suitability question",
                difficulty="medium"
            ),
            
            # Comparison Questions
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.COMPARISON,
                template="{brand_name}与同类品牌相比有什么优势？",
                description="Competitive advantage question",
                difficulty="medium"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.COMPARISON,
                template="{brand_name}和竞品的主要区别是什么？",
                description="Direct competitor comparison",
                difficulty="medium"
            ),
            QuestionTemplate(
                id=str(uuid.uuid4()),
                category=QuestionCategory.COMPARISON,
                template="为什么用户应该选择{brand_name}而不是其他品牌？",
                description="Preference justification question",
                difficulty="hard"
            ),
        ]
        
        db_logger.info(f"Loaded {len(templates)} standard question templates")
        return templates
    
    def get_templates_by_category(self, category: QuestionCategory) -> List[QuestionTemplate]:
        """Get all templates for a specific category"""
        return [t for t in self.standard_templates if t.category == category and t.is_active]
    
    def get_all_templates(self) -> List[QuestionTemplate]:
        """Get all active standard templates"""
        return [t for t in self.standard_templates if t.is_active]
    
    def validate_custom_questions(self, questions: List[str]) -> Dict[str, any]:
        """
        Validate custom questions according to business rules
        
        Args:
            questions: List of custom question strings
            
        Returns:
            Dict with validation results
        """
        result = {
            'valid': True,
            'errors': [],
            'cleaned_questions': []
        }
        
        # Check number of questions (1-5)
        if len(questions) < 1:
            result['valid'] = False
            result['errors'].append("At least 1 question is required")
        elif len(questions) > 5:
            result['valid'] = False
            result['errors'].append("Maximum 5 questions allowed")
        
        # Validate and clean each question
        for i, question in enumerate(questions):
            cleaned_question = self.clean_question_text(question)
            
            if not cleaned_question.strip():
                result['valid'] = False
                result['errors'].append(f"Question {i+1} is empty after cleaning")
                continue
                
            if len(cleaned_question) < 5:
                result['valid'] = False
                result['errors'].append(f"Question {i+1} is too short (minimum 5 characters)")
                continue
                
            if len(cleaned_question) > 500:
                result['valid'] = False
                result['errors'].append(f"Question {i+1} is too long (maximum 500 characters)")
                continue
            
            result['cleaned_questions'].append(cleaned_question)
        
        return result
    
    def clean_question_text(self, text: str) -> str:
        """
        Clean question text by removing extra whitespace and normalizing
        
        Args:
            text: Raw question text
            
        Returns:
            Cleaned question text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove leading/trailing punctuation that might be accidentally included
        cleaned = cleaned.strip('.,;:!?')
        
        # Capitalize first letter if it's lowercase
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        return cleaned
    
    def create_custom_questions(self, raw_questions: List[str]) -> List[CustomQuestion]:
        """
        Create custom question objects from raw question strings
        
        Args:
            raw_questions: List of raw question strings
            
        Returns:
            List of CustomQuestion objects
        """
        validation_result = self.validate_custom_questions(raw_questions)
        
        if not validation_result['valid']:
            raise ValueError(f"Invalid questions: {'; '.join(validation_result['errors'])}")
        
        custom_questions = []
        for raw_question in validation_result['cleaned_questions']:
            custom_question = CustomQuestion(
                id=str(uuid.uuid4()),
                content=raw_question,
                original_content=raw_question
            )
            custom_questions.append(custom_question)
        
        db_logger.info(f"Created {len(custom_questions)} custom questions")
        return custom_questions