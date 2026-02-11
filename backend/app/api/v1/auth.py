"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_user,
    get_current_user,
    get_db,
    get_optional_current_user,
)
from app.models import User
from app.schemas.responses import ErrorResponse, SingleResponse, SuccessResponse
from app.schemas.user import (
    ChangePassword,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserStats,
    UserUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=SingleResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Email already registered"}
    }
)
async def register(
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
async def login(
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
    return Token(**tokens)


@router.post(
    "/refresh",
    response_model=Token
)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token."""
    auth_service = AuthService(db)
    tokens = auth_service.create_tokens(str(current_user.id))
    return Token(**tokens)


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
    # TODO: Implement proper stats calculation
    # For now, return basic stats
    
    stats = UserStats(
        total_reads=current_user.total_reads,
        streak_days=current_user.streak_days,
        weekly_goal=current_user.weekly_goal,
        weekly_progress=min(current_user.total_reads % 7, current_user.weekly_goal),
        skill_badges_count=len(current_user.skill_badges),
        saved_items_count=0,  # TODO: Query actual count
        favorite_categories=[]  # TODO: Calculate from history
    )
    
    return SingleResponse(data=stats)


@router.post(
    "/logout",
    response_model=SuccessResponse
)
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """Logout (client should discard tokens)."""
    # JWT tokens are stateless, so we just tell client to discard them
    # For token revocation, we'd need a blacklist (Redis recommended)
    return SuccessResponse(message="Logged out successfully")
