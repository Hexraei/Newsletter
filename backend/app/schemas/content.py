"""Schemas for AI and content feed endpoints."""

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# AI request schemas
class SummarizeRequest(BaseModel):
    """Request to summarize content."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10, max_length=50000)
    category: str = Field(default="tech", max_length=50)


class HeadlineRequest(BaseModel):
    """Request to generate a headline."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="", max_length=50000)


class EmbedRequest(BaseModel):
    """Request to generate text embedding."""
    text: str = Field(..., min_length=1, max_length=10000)


# Feed request schemas
class FeedbackRequest(BaseModel):
    """Request to submit content feedback."""
    feedback_type: str = Field(..., pattern="^(like|dislike|report|helpful)$")
    reason: Optional[str] = Field(None, max_length=500)
    reported_issue: Optional[str] = Field(None, max_length=50)

    @field_validator('reason', mode='before')
    @classmethod
    def sanitize_reason(cls, v):
        if v is None:
            return v
        v = re.sub(r'<[^>]+>', '', v).strip()
        if not v:
            return None
        return v

    @field_validator('reported_issue', mode='before')
    @classmethod
    def sanitize_issue(cls, v):
        if v is None:
            return v
        v = re.sub(r'<[^>]+>', '', v)
        return v.strip()[:50]
