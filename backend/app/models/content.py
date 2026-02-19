"""Content models for scraped and processed content."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Source(Base):
    """Content sources configuration."""
    
    __tablename__ = "sources"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Scraping config
    scrape_config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}"
    )
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rate_limit: Mapped[int] = mapped_column(Integer, default=60)
    proxy_tier: Mapped[str] = mapped_column(String(20), default="standard")
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    success_rate: Mapped[float] = mapped_column(default=100.0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Classification
    default_categories: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}"
    )
    default_tags: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}"
    )
    department_tags: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}"
    )


class RawContent(Base):
    """Raw scraped content before processing."""
    
    __tablename__ = "raw_content"
    
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id"),
        nullable=False
    )
    
    # Original data
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Metadata
    raw_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}"
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False
    )
    
    # Processing status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationship
    source: Mapped["Source"] = relationship("Source", lazy="selectin")


class ProcessedContent(Base):
    """Processed content ready for display."""
    
    __tablename__ = "processed_content"
    
    raw_content_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_content.id"),
        nullable=True
    )
    
    # Optimized for reading
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_blocks: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True
    )
    reading_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Categorization
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department_tags: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}"
    )
    topic_tags: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}"
    )
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Quality scoring
    quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    relevance_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    priority_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attractiveness_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Breaking news
    is_breaking: Mapped[bool] = mapped_column(Boolean, default=False)
    breaking_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    breaking_detected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Media
    featured_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visualizations: Mapped[Optional[list]] = mapped_column(
        JSONB,
        default=list,
        server_default="{}"
    )
    
    # Engagement
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    save_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Publishing
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    weekly_bucket: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Content type
    content_type: Mapped[str] = mapped_column(
        String(20),
        default="news",
        nullable=False
    )  # 'news', 'opportunity', 'story'
    
    # Opportunity-specific fields
    opportunity_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    opportunity_pay: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    opportunity_source_platform: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )


class VectorEmbedding(Base):
    """Vector embeddings for content."""
    
    __tablename__ = "vector_embeddings"
    
    content_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processed_content.id"),
        nullable=False
    )
    
    # Store as JSON array for compatibility
    embedding: Mapped[list] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Relationships
    content: Mapped["ProcessedContent"] = relationship(
        "ProcessedContent",
        lazy="selectin"
    )


class HooklineQueue(Base):
    """Queue for hookline/headline generation."""
    
    __tablename__ = "hookline_queue"
    
    content_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processed_content.id"),
        nullable=False
    )
    
    original_title: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_hook: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )  # pending, processing, completed, failed
    
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )


class BreakingAlert(Base):
    """Breaking news alerts."""
    
    __tablename__ = "breaking_alerts"
    
    content_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processed_content.id"),
        nullable=False
    )
    
    alert_level: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_score: Mapped[int] = mapped_column(Integer, nullable=False)
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_required: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Cross-platform validation
    platforms_detected: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}"
    )
    detection_confidence: Mapped[float] = mapped_column(default=0.0)
    
    # Notification status
    notifications_sent: Mapped[int] = mapped_column(Integer, default=0)
    notifications_opened: Mapped[int] = mapped_column(Integer, default=0)
    
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )


class VelocityMetrics(Base):
    """Velocity tracking for breaking news detection."""
    
    __tablename__ = "velocity_metrics"
    
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id"),
        nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    hour_bucket: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    engagement_count: Mapped[int] = mapped_column(Integer, default=0)
    velocity_score: Mapped[float] = mapped_column(default=0.0)
    
    is_breaking_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
