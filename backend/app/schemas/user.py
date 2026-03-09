"""User schemas for API requests and responses."""

import json
import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# Shared properties
class UserBase(BaseModel):
    """Base user schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = True


# Properties to receive via API on creation
class UserCreate(UserBase):
    """User creation schema."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    year_of_study: Optional[int] = Field(None, ge=1, le=5)
    college_name: Optional[str] = Field(None, max_length=200)

    @field_validator('full_name', mode='before')
    @classmethod
    def validate_full_name(cls, v):
        if v is not None:
            v = re.sub(r'<[^>]+>', '', v).strip()
            if not v:
                raise ValueError('Full name cannot be empty')
        return v


# Properties to receive via API on update
class UserUpdate(UserBase):
    """User update schema."""
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    department: Optional[str] = Field(None, max_length=100)
    year_of_study: Optional[int] = Field(None, ge=1, le=5)
    graduation_year: Optional[int] = None
    college_name: Optional[str] = Field(None, max_length=200)
    interests: Optional[List[str]] = None
    content_preferences: Optional[dict] = None
    notification_settings: Optional[dict] = None

    @field_validator('interests', mode='before')
    @classmethod
    def validate_interests(cls, v):
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError('Maximum 20 interests allowed')
        for item in v:
            if not isinstance(item, str):
                raise ValueError('Each interest must be a string')
            if len(item) > 50:
                raise ValueError('Each interest must be 50 characters or less')
            if not item.strip():
                raise ValueError('Empty interests not allowed')
        return [item.strip() for item in v]

    @field_validator('content_preferences', mode='before')
    @classmethod
    def validate_preferences(cls, v):
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError('Preferences must be a JSON object')
        serialized = json.dumps(v)
        if len(serialized) > 5000:
            raise ValueError('Preferences too large (max 5KB)')
        return v

    @field_validator('notification_settings', mode='before')
    @classmethod
    def validate_notifications(cls, v):
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError('Notification settings must be a JSON object')
        allowed_keys = {'email_digest', 'breaking_news', 'weekly_summary', 'frequency'}
        unknown = set(v.keys()) - allowed_keys
        if unknown:
            raise ValueError(f'Unknown notification settings: {unknown}')
        return v


# Properties stored in database
class UserInDB(UserBase):
    """User in database schema."""
    id: str
    department: Optional[str] = None
    department_key: Optional[str] = None
    year_of_study: Optional[int] = None
    graduation_year: Optional[int] = None
    college_name: Optional[str] = None
    interests: List[str] = []
    content_preferences: dict = {}
    notification_settings: dict = {}
    streak_days: int = 0
    total_reads: int = 0
    skill_badges: List[str] = []
    weekly_goal: int = 7
    is_admin: bool = False
    email_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


# Properties to return via API
class UserResponse(UserInDB):
    """User response schema."""
    pass


# User profile response (public info)
class UserProfile(BaseModel):
    """Public user profile."""
    id: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    department: Optional[str] = None
    year_of_study: Optional[int] = None
    college_name: Optional[str] = None
    streak_days: int = 0
    skill_badges: List[str] = []


# Login schemas
class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[str] = None
    type: Optional[str] = None
    exp: Optional[datetime] = None


# Password reset schemas
class PasswordReset(BaseModel):
    """Password reset request schema."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    token: str
    new_password: str = Field(..., min_length=8)


# User stats schema
class UserStats(BaseModel):
    """User statistics schema."""
    total_reads: int
    streak_days: int
    weekly_goal: int
    weekly_progress: int
    skill_badges_count: int
    saved_items_count: int
    favorite_categories: List[dict]


# Change password schema
class ChangePassword(BaseModel):
    """Change password schema."""
    current_password: str
    new_password: str = Field(..., min_length=8)
