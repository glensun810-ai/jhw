"""
Cleaning Pipeline Configuration

Centralized configuration for the cleaning pipeline.
"""

from typing import Dict, Any


# Default pipeline configuration
DEFAULT_PIPELINE_CONFIG: Dict[str, Any] = {
    'stop_on_error': True,      # Stop on error
    'continue_on_warning': True,  # Continue on warning
    'parallel_steps': False,     # Whether to execute steps in parallel
    'timeout': 30,              # Total timeout in seconds
}

# Text extractor default configuration
TEXT_EXTRACTOR_CONFIG: Dict[str, Any] = {
    'strip_html': True,
    'unescape_html': True,
    'normalize_whitespace': True,
    'max_length': 10000,
    'min_length': 10,
}

# Entity recognizer default configuration
ENTITY_RECOGNIZER_CONFIG: Dict[str, Any] = {
    'case_sensitive': False,
    'min_confidence': 0.8,
    'enable_partial_match': False,
    'max_entities': 100,
}

# Deduplicator default configuration
DEDUPLICATOR_CONFIG: Dict[str, Any] = {
    'method': 'exact_hash',  # exact_hash, simhash
    'similarity_threshold': 0.95,
    'store_hashes': True,
}

# Validator default configuration
VALIDATOR_CONFIG: Dict[str, Any] = {
    'rules': [
        'min_length',
        'max_length',
        'no_empty',
        'valid_encoding',
        'no_invalid_chars'
    ],
    'min_length': 10,
    'max_length': 10000,
    'invalid_chars': ['\x00', '\x01', '\x02'],
}

# GEO preparer default configuration
GEO_PREPARER_CONFIG: Dict[str, Any] = {
    'detect_language': True,
    'extract_urls': True,
    'extract_numbers': True,
    'split_sentences': True,
    'max_sentences': 100,
}

# Quality scorer default configuration
QUALITY_SCORER_CONFIG: Dict[str, Any] = {
    'weights': {
        'length': 0.3,
        'completeness': 0.4,
        'relevance': 0.3,
    },
    'ideal_length': 500,
    'min_acceptable_length': 50,
    'max_acceptable_length': 2000,
}
