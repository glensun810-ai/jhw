"""
Deduplication Step

Detects and marks duplicate content to avoid repeated statistics.
"""

import hashlib
from typing import Dict, Any, Set, List

from wechat_backend.v2.cleaning.steps.base import CleaningStep
from wechat_backend.v2.cleaning.models.pipeline_context import PipelineContext


class DeduplicatorStep(CleaningStep):
    """
    Deduplication step

    Detects and marks duplicate content using SimHash or simple hash.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('deduplicator', config)

        # Default configuration
        self.config.setdefault('method', 'exact_hash')  # exact_hash, simhash
        self.config.setdefault('similarity_threshold', 0.95)
        self.config.setdefault('store_hashes', True)

        # Hash store for cross-task deduplication (should use Redis in production)
        self._hash_store: Set[str] = set()

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Execute deduplication detection"""

        # 1. Get text
        text = context.response_content
        if not text:
            context.add_warning("Empty text for deduplication")
            return context

        # 2. Calculate hash
        if self.config['method'] == 'exact_hash':
            content_hash = self._compute_exact_hash(text)
        else:
            content_hash = self._compute_simhash(text)

        # 3. Check if duplicate
        is_duplicate = self._check_duplicate(content_hash, context)

        # 4. Save results
        result = {
            'content_hash': content_hash,
            'is_duplicate': is_duplicate,
            'method': self.config['method'],
        }

        self.save_step_result(context, result)

        # 5. Add warning if duplicate
        if is_duplicate:
            context.add_warning("Duplicate content detected")

        return context

    def _compute_exact_hash(self, text: str) -> str:
        """Compute exact hash"""
        # Normalize text (remove spaces, punctuation, etc.)
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _compute_simhash(self, text: str) -> str:
        """Compute SimHash (simplified version)"""
        # Simplified implementation, actual should use real SimHash algorithm
        # Here using chunked hash as alternative
        chunks = self._split_into_chunks(text, 50)
        hashes = []

        for chunk in chunks:
            h = hashlib.md5(chunk.encode('utf-8')).hexdigest()
            hashes.append(h)

        # Combine hashes
        combined = ''.join(sorted(hashes))
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def _normalize_text(self, text: str) -> str:
        """Normalize text (for deduplication preprocessing)"""
        # Remove punctuation
        import string
        text = text.translate(str.maketrans('', '', string.punctuation + string.punctuation))
        # Convert to lowercase
        text = text.lower()
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    def _split_into_chunks(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    def _check_duplicate(self, content_hash: str, context: PipelineContext) -> bool:
        """Check if duplicate"""
        # Check if duplicate in current context
        # For cross-execution deduplication, would need shared storage
        # Here we just check within current batch via intermediate_data
        existing_hashes = context.intermediate_data.get('dedup_hashes', set())
        
        if content_hash in existing_hashes:
            return True

        # Store hash for future use
        if self.config['store_hashes']:
            existing_hashes.add(content_hash)
            context.intermediate_data['dedup_hashes'] = existing_hashes
            self._hash_store.add(content_hash)

        return False

    def should_skip(self, context: PipelineContext) -> bool:
        """Skip if text is empty"""
        return not context.response_content
