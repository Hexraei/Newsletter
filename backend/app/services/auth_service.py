"""Authentication service for user management."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models import User
from app.departments import DEPARTMENT_KEYS, DEPARTMENTS
from app.schemas.user import UserCreate, UserUpdate


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("Email already registered")
        
        # Resolve department key
        dept_val = user_data.department
        dept_key = None
        dept_name = dept_val
        if dept_val and dept_val.upper() in DEPARTMENT_KEYS:
            dept_key = dept_val.upper()
            dept_name = next((d["name"] for d in DEPARTMENTS if d["key"] == dept_key), dept_val)

        # Create new user
        db_user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            department=dept_name,
            department_key=dept_key,
            year_of_study=user_data.year_of_study,
            college_name=user_data.college_name,
        )
        
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        
        return db_user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return user
    
    async def update_user(self, user: User, user_data: UserUpdate) -> User:
        """Update user information."""
        ALLOWED_FIELDS = {"full_name", "department", "year_of_study", "college_name", "password"}
        update_data = user_data.model_dump(exclude_unset=True)
        
        # Filter to only allowed fields — block is_admin, is_active, etc.
        update_data = {k: v for k, v in update_data.items() if k in ALLOWED_FIELDS}
        
        # Handle password separately
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(
                update_data.pop("password")
            )
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password."""
        if not verify_password(current_password, user.password_hash):
            return False
        
        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
        
        return True
    
    def create_tokens(self, user_id: str) -> dict:
        """Create access and refresh tokens for user."""
        access_token = create_access_token(subject=user_id)
        refresh_token = create_refresh_token(subject=user_id)
        
        from app.config import settings
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    async def generate_reset_token(self, email: str) -> Optional[str]:
        """Generate a password reset token for the given email. Returns the token, or None if user not found."""
        user = await self.get_user_by_email(email)
        if not user:
            return None

        token = secrets.token_urlsafe(64)
        user.reset_token = token
        user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        await self.db.commit()
        return token

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password using a valid reset token."""
        result = await self.db.execute(
            select(User).where(User.reset_token == token)
        )
        user = result.scalar_one_or_none()

        if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.now(timezone.utc):
            if user:
                user.reset_token = None
                user.reset_token_expiry = None
                await self.db.commit()
            return False

        user.password_hash = get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        await self.db.commit()
        return True

    async def deactivate_user(self, user: User) -> None:
        """Deactivate user account."""
        user.is_active = False
        await self.db.commit()
