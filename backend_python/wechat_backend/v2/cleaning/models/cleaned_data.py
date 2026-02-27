"""
Cleaning Pipeline Data Models

Defines the data structures used throughout the cleaning pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class EntityMention:
    """Entity mention information"""
    entity_name: str                         # Entity name (brand/competitor)
    entity_type: str                          # Entity type: 'brand', 'competitor'
    start_pos: int                             # Start position in text
    end_pos: int                               # End position in text
    confidence: float = 1.0                    # Confidence score
    context: Optional[str] = None               # Context snippet


@dataclass
class GeoPreparedData:
    """GEO analysis prepared data"""
    text_length: int                           # Text length
    sentence_count: int                         # Number of sentences
    has_brand_mention: bool = False              # Whether brand is mentioned
    brand_positions: List[int] = field(default_factory=list)  # Brand positions
    competitor_mentions: Dict[str, int] = field(default_factory=dict)  # Competitor mention counts
    language: str = 'zh'                         # Language
    contains_numbers: bool = False                # Whether contains numbers
    contains_urls: bool = False                   # Whether contains URLs


@dataclass
class QualityScore:
    """Quality score"""
    overall_score: float = 0.0                    # Overall score 0-100
    length_score: float = 0.0                      # Length score
    completeness_score: float = 0.0                 # Completeness score
    relevance_score: float = 0.0                    # Relevance score
    issues: List[str] = field(default_factory=list)  # Issues found
    warnings: List[str] = field(default_factory=list) # Warning messages


@dataclass
class CleanedData:
    """
    Cleaned data model

    This is the standard output format after the cleaning pipeline,
    all subsequent statistical analysis is based on this model.
    """
    # Original references
    execution_id: str
    report_id: int
    result_id: Optional[int] = None                 # Associated original result ID

    # Basic information
    brand: str
    question: str
    model: str

    # Cleaned text
    cleaned_text: str                               # Cleaned plain text
    original_text: str                              # Original text (backup)

    # Entity information
    entities: List[EntityMention] = field(default_factory=list)

    # GEO prepared data
    geo_data: Optional[GeoPreparedData] = None

    # Quality score
    quality: Optional[QualityScore] = None

    # Cleaning metadata
    cleaning_version: str = '1.0'
    steps_applied: List[str] = field(default_factory=list)  # Applied cleaning steps
    warnings: List[str] = field(default_factory=list)       # Warnings during cleaning
    errors: List[str] = field(default_factory=list)         # Errors during cleaning

    # Timestamp
    cleaned_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for storage)"""
        return {
            'execution_id': self.execution_id,
            'report_id': self.report_id,
            'result_id': self.result_id,
            'brand': self.brand,
            'question': self.question,
            'model': self.model,
            'cleaned_text': self.cleaned_text,
            'original_text': self.original_text,
            'entities': [
                {
                    'entity_name': e.entity_name,
                    'entity_type': e.entity_type,
                    'confidence': e.confidence
                }
                for e in self.entities
            ],
            'geo_data': {
                'text_length': self.geo_data.text_length,
                'sentence_count': self.geo_data.sentence_count,
                'has_brand_mention': self.geo_data.has_brand_mention,
                'brand_positions': self.geo_data.brand_positions,
                'competitor_mentions': self.geo_data.competitor_mentions,
                'language': self.geo_data.language
            } if self.geo_data else None,
            'quality': {
                'overall_score': self.quality.overall_score,
                'length_score': self.quality.length_score,
                'completeness_score': self.quality.completeness_score,
                'relevance_score': self.quality.relevance_score,
                'issues': self.quality.issues,
                'warnings': self.quality.warnings
            } if self.quality else None,
            'cleaning_version': self.cleaning_version,
            'steps_applied': self.steps_applied,
            'warnings': self.warnings,
            'errors': self.errors,
            'cleaned_at': self.cleaned_at.isoformat(),
        }

    @classmethod
    def from_response(cls, response: Any, execution_id: str, report_id: int, brand: str, question: str, model: str) -> 'CleanedData':
        """
        Create cleaned data object from raw response (initialization)

        Note: This just creates a shell, actual cleaning is done by the pipeline
        """
        return cls(
            execution_id=execution_id,
            report_id=report_id,
            brand=brand,
            question=question,
            model=model,
            cleaned_text='',
            original_text='',
        )
