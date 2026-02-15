"""Schemas for AI and content feed endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field


# AI request schemas
class SummarizeRequest(BaseModel):
    """Request to summarize content."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    category: str = Field(default="tech", max_length=50)


class HeadlineRequest(BaseModel):
    """Request to generate a headline."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="")


class EmbedRequest(BaseModel):
    """Request to generate text embedding."""
    text: str = Field(..., min_length=1)


# Feed request schemas
class FeedbackRequest(BaseModel):
    """Request to submit content feedback."""
    feedback_type: str = Field(..., pattern="^(like|dislike|report|helpful)$")
    reason: Optional[str] = Field(None, max_length=500)
    reported_issue: Optional[str] = Field(None, max_length=50)
