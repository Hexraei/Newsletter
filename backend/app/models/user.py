"""User model for authentication and profiles."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.content import ProcessedContent, UserFeedback, UserReads, UserSaves


class User(Base):
    """User model for authentication and user profiles."""
    
    __tablename__ = "users"
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Academic Info
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department_key: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    year_of_study: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    college_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Preferences
    interests: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}"
    )
    content_preferences: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}"
    )
    notification_settings: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {
            "email_digest": True,
            "breaking_news": True,
            "weekly_summary": True
        },
        server_default='{"email_digest": true, "breaking_news": true, "weekly_summary": true}'
    )
    
    # Gamification
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    total_reads: Mapped[int] = mapped_column(Integer, default=0)
    skill_badges: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}"
    )
    weekly_goal: Mapped[int] = mapped_column(Integer, default=7)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    reads: Mapped[List["UserReads"]] = relationship(
        "UserReads",
        back_populates="user",
        lazy="selectin"
    )
    saves: Mapped[List["UserSaves"]] = relationship(
        "UserSaves",
        back_populates="user",
        lazy="selectin"
    )
    feedback: Mapped[List["UserFeedback"]] = relationship(
        "UserFeedback",
        back_populates="user",
        lazy="selectin"
    )


class UserReads(Base):
    """User reading history."""
    
    __tablename__ = "user_reads"
    
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    content_id: Mapped[str] = mapped_column(
        ForeignKey("processed_content.id", ondelete="CASCADE"),
        nullable=False
    )
    
    read_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reads")


class UserSaves(Base):
    """User saved/bookmarked content."""
    
    __tablename__ = "user_saves"
    
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    content_id: Mapped[str] = mapped_column(
        ForeignKey("processed_content.id", ondelete="CASCADE"),
        nullable=False
    )
    collection_name: Mapped[str] = mapped_column(String(100), default="default")
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="saves")


class UserFeedback(Base):
    """User feedback on content."""
    
    __tablename__ = "user_feedback"
    
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    content_id: Mapped[str] = mapped_column(
        ForeignKey("processed_content.id", ondelete="CASCADE"),
        nullable=False
    )
    
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reported_issue: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="feedback")
