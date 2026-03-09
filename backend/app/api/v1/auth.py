"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_user,
    get_current_user,
    get_db,
    get_optional_current_user,
)
from app.config import settings
from app.models import User
from app.schemas.responses import ErrorResponse, SingleResponse, SuccessResponse
from app.schemas.user import (
    ChangePassword,
    PasswordReset,
    PasswordResetConfirm,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserStats,
    UserUpdate,
)
from app.services.auth_service import AuthService
from app.services.email_service import send_reset_email

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str):
    """Set httpOnly authentication cookies on the response."""
    is_secure = settings.COOKIE_SECURE
    domain = settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None
    samesite = settings.COOKIE_SAMESITE

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite=samesite,
        domain=domain,
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite=samesite,
        domain=domain,
        path="/api/v1/auth/refresh",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


@router.post(
    "/register",
    response_model=SingleResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Email already registered"}
    }
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.create_user(user_data)
        return SingleResponse(data=user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/login",
    response_model=Token
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password."""
    auth_service = AuthService(db)
    
    user = await auth_service.authenticate_user(
        credentials.email,
        credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    tokens = auth_service.create_tokens(str(user.id))
    token_data = Token(**tokens)
    response = JSONResponse(content=token_data.model_dump())
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return response


@router.post(
    "/refresh",
    response_model=Token
)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token."""
    auth_service = AuthService(db)
    tokens = auth_service.create_tokens(str(current_user.id))
    token_data = Token(**tokens)
    response = JSONResponse(content=token_data.model_dump())
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return response


@router.get(
    "/me",
    response_model=SingleResponse[UserResponse]
)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile."""
    return SingleResponse(data=current_user)


@router.put(
    "/me",
    response_model=SingleResponse[UserResponse]
)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    auth_service = AuthService(db)
    updated_user = await auth_service.update_user(current_user, user_data)
    return SingleResponse(data=updated_user)


@router.post(
    "/change-password",
    response_model=SuccessResponse
)
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    auth_service = AuthService(db)
    
    success = await auth_service.change_password(
        current_user,
        password_data.current_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    return SuccessResponse(message="Password changed successfully")


@router.get(
    "/stats",
    response_model=SingleResponse[UserStats]
)
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics."""
    from sqlalchemy import select, func
    from app.models import UserSaves, UserReads, ProcessedContent
    
    # Count saved items
    result = await db.execute(
        select(func.count(UserSaves.id))
        .where(UserSaves.user_id == str(current_user.id))
    )
    saved_count = result.scalar() or 0
    
    # Calculate favorite categories from reading history
    result = await db.execute(
        select(ProcessedContent.category, func.count(ProcessedContent.id))
        .join(UserReads, UserReads.content_id == ProcessedContent.id)
        .where(UserReads.user_id == str(current_user.id))
        .where(ProcessedContent.category.isnot(None))
        .group_by(ProcessedContent.category)
        .order_by(func.count(ProcessedContent.id).desc())
        .limit(5)
    )
    fav_categories = [
        {"category": row[0], "count": row[1]}
        for row in result.all()
    ]
    
    stats = UserStats(
        total_reads=current_user.total_reads,
        streak_days=current_user.streak_days,
        weekly_goal=current_user.weekly_goal,
        weekly_progress=min(current_user.total_reads % 7, current_user.weekly_goal),
        skill_badges_count=len(current_user.skill_badges),
        saved_items_count=saved_count,
        favorite_categories=fav_categories
    )
    
    return SingleResponse(data=stats)


@router.post(
    "/forgot-password",
    response_model=SuccessResponse
)
@limiter.limit("5/hour")
async def forgot_password(
    request: Request,
    body: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """Request a password reset link. Always returns success to prevent email enumeration."""
    auth_service = AuthService(db)
    token = await auth_service.generate_reset_token(body.email)

    if token:
        base_url = str(request.base_url).rstrip("/")
        await send_reset_email(body.email, token, base_url)

    return SuccessResponse(message="If an account exists, a reset link has been sent.")


@router.post(
    "/reset-password",
    response_model=SuccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired token"}
    }
)
@limiter.limit("5/hour")
async def reset_password(
    request: Request,
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using a valid reset token."""
    auth_service = AuthService(db)
    success = await auth_service.reset_password(body.token, body.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    return SuccessResponse(message="Password has been reset successfully.")


@router.post(
    "/logout",
    response_model=SuccessResponse
)
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """Logout (clears auth cookies; client should also discard any stored session)."""
    response = JSONResponse(content={"success": True, "message": "Logged out successfully"})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    return response


@router.delete(
    "/me",
    response_model=SuccessResponse
)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete user account and all associated data (GDPR right to erasure)."""
    from app.models import UserSaves, UserReads, UserFeedback
    await db.execute(delete(UserSaves).where(UserSaves.user_id == str(current_user.id)))
    await db.execute(delete(UserReads).where(UserReads.user_id == str(current_user.id)))
    await db.execute(delete(UserFeedback).where(UserFeedback.user_id == str(current_user.id)))
    await db.delete(current_user)
    await db.commit()
    return SuccessResponse(message="Account and all associated data deleted")
