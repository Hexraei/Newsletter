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
    summary="Register new user",
    description="Creates a new user account with email, password, and optional profile information. "
                "Rate limited to 3 registrations per hour per IP.",
    response_model=SingleResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User registered successfully"},
        400: {"model": ErrorResponse, "description": "Email already registered"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account.

    Creates the account with a hashed password. Returns the new user profile.
    Rate limited to 3 registrations per hour per IP address.
    """
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
    summary="Login",
    description="Authenticates a user with email and password. Returns JWT tokens and sets httpOnly auth cookies. "
                "Rate limited to 5 attempts per minute per IP.",
    response_model=Token,
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"description": "Incorrect email or password"},
        403: {"description": "User account is inactive"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password.

    Returns access and refresh tokens as both JSON body and httpOnly cookies.
    Rate limited to 5 attempts per minute per IP address.
    """
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
    summary="Refresh access token",
    description="Issues new access and refresh tokens using the current valid session. "
                "Rate limited to 10 refreshes per minute.",
    response_model=Token,
    responses={
        200: {"description": "New tokens issued"},
        401: {"description": "Invalid or expired token"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token.

    Issues a new access/refresh token pair. The current token must still be valid.
    New tokens are returned as both JSON body and httpOnly cookies.
    """
    auth_service = AuthService(db)
    tokens = auth_service.create_tokens(str(current_user.id))
    token_data = Token(**tokens)
    response = JSONResponse(content=token_data.model_dump())
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return response


@router.get(
    "/me",
    summary="Get current user profile",
    description="Returns the authenticated user's profile information including department, interests, and settings.",
    response_model=SingleResponse[UserResponse],
    responses={
        200: {"description": "User profile data"},
        401: {"description": "Not authenticated"},
    }
)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """Get the current authenticated user's profile.

    Returns all profile fields including department, interests, and streak data.
    """
    return SingleResponse(data=current_user)


@router.put(
    "/me",
    summary="Update current user profile",
    description="Updates the authenticated user's profile fields such as name, department, interests, and weekly goal.",
    response_model=SingleResponse[UserResponse],
    responses={
        200: {"description": "Updated user profile"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid update data"},
    }
)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update the current user's profile.

    Accepts partial updates — only provided fields are changed.
    """
    auth_service = AuthService(db)
    updated_user = await auth_service.update_user(current_user, user_data)
    return SingleResponse(data=updated_user)


@router.post(
    "/change-password",
    summary="Change password",
    description="Changes the authenticated user's password. Requires the current password for verification.",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Incorrect current password"},
        401: {"description": "Not authenticated"},
    }
)
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change the authenticated user's password.

    Requires the current password for verification before setting the new one.
    """
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
    summary="Get user statistics",
    description="Returns reading statistics for the authenticated user including streak days, saved items, and favorite categories.",
    response_model=SingleResponse[UserStats],
    responses={
        200: {"description": "User statistics"},
        401: {"description": "Not authenticated"},
    }
)
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the authenticated user's reading statistics.

    Includes total reads, streak days, weekly goal progress,
    skill badge count, saved items count, and top 5 favorite categories.
    """
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
    summary="Request password reset",
    description="Sends a password reset link to the provided email address if an account exists. "
                "Always returns success to prevent email enumeration. Rate limited to 5 per hour.",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Reset email sent (or account does not exist)"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/hour")
async def forgot_password(
    request: Request,
    body: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """Request a password reset link.

    Always returns success to prevent email enumeration.
    If the account exists, a reset link is sent via email.
    """
    auth_service = AuthService(db)
    token = await auth_service.generate_reset_token(body.email)

    if token:
        base_url = str(request.base_url).rstrip("/")
        await send_reset_email(body.email, token, base_url)

    return SuccessResponse(message="If an account exists, a reset link has been sent.")


@router.post(
    "/reset-password",
    summary="Reset password with token",
    description="Resets the user's password using a valid reset token obtained from the forgot-password flow. "
                "Rate limited to 5 attempts per hour.",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Password reset successfully"},
        400: {"model": ErrorResponse, "description": "Invalid or expired token"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/hour")
async def reset_password(
    request: Request,
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using a valid reset token.

    The token is single-use and expires after a configured time period.
    """
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
    summary="Logout",
    description="Logs out the current user by clearing httpOnly auth cookies. "
                "The client should also discard any stored tokens.",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Logged out successfully"},
        401: {"description": "Not authenticated"},
    }
)
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """Logout the current user.

    Clears httpOnly auth cookies. The client should also discard
    any locally stored tokens or session data.
    """
    response = JSONResponse(content={"success": True, "message": "Logged out successfully"})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    return response


@router.delete(
    "/me",
    summary="Delete account",
    description="Permanently deletes the authenticated user's account and all associated data "
                "including saves, reading history, and feedback (GDPR right to erasure).",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Account and all data deleted"},
        401: {"description": "Not authenticated"},
    }
)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete user account and all associated data.

    Permanently removes the user account along with saves, reading history,
    and feedback records (GDPR right to erasure). This action is irreversible.
    """
    from app.models import UserSaves, UserReads, UserFeedback
    await db.execute(delete(UserSaves).where(UserSaves.user_id == str(current_user.id)))
    await db.execute(delete(UserReads).where(UserReads.user_id == str(current_user.id)))
    await db.execute(delete(UserFeedback).where(UserFeedback.user_id == str(current_user.id)))
    await db.delete(current_user)
    await db.commit()
    return SuccessResponse(message="Account and all associated data deleted")
