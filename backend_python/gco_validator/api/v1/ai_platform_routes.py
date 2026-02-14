"""
AI Platform-related API routes for GEO Content Quality Validator
"""
from fastapi import APIRouter
from typing import List

from gco_validator.schemas.test_schemas import AIPlatformsResponse, AIPlatform

router = APIRouter()


@router.get("/", response_model=AIPlatformsResponse)
async def get_ai_platforms() -> AIPlatformsResponse:
    """
    Get list of supported AI platforms
    """
    platforms = AIPlatformsResponse(
        domestic=[
            AIPlatform(name='DeepSeek', checked=False),
            AIPlatform(name='豆包', checked=False),
            AIPlatform(name='元宝', checked=False),
            AIPlatform(name='通义千问', checked=True),
            AIPlatform(name='文心一言', checked=False),
            AIPlatform(name='Kimi', checked=True),
            AIPlatform(name='讯飞星火', checked=False)
        ],
        overseas=[
            AIPlatform(name='ChatGPT', checked=True),
            AIPlatform(name='Claude', checked=True),
            AIPlatform(name='Gemini', checked=False),
            AIPlatform(name='Perplexity', checked=False),
            AIPlatform(name='Grok', checked=False)
        ]
    )
    return platforms