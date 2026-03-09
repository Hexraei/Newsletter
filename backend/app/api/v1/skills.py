"""API endpoints for placement skill rankings."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_optional_current_user
from app.departments import DEPARTMENT_KEYS
from app.models import User
from app.services.skills_service import SkillsService

router = APIRouter()


class TrackSkillRequest(BaseModel):
    skill_name: str


@router.get(
    "/departments",
    summary="List skill departments",
    description="Returns the list of departments that have placement skill data available.",
    responses={200: {"description": "List of departments with skill data"}},
)
async def list_skill_departments():
    """List departments that have skill ranking data.

    Returns department keys for which placement skill information is available.
    """
    return {"departments": SkillsService.get_available_departments()}


@router.get(
    "/{department}",
    summary="Get department skills",
    description="Returns ranked placement skills for a department, optionally filtered by category. "
                "Includes the user's tracked skills if authenticated.",
    responses={
        200: {"description": "Ranked skills with optional user tracking data"},
        404: {"description": "Department not found or no skill data available"},
    },
)
async def get_skills(
    department: str = Path(description="Department key (e.g., CSE, IT, AIDS, ECE)"),
    category: Optional[str] = Query(None, pattern="^(core|tool|soft)$", description="Filter by skill category: core, tool, or soft"),
    sort_by: str = Query("rating", pattern="^(rating|name)$", description="Sort skills by rating or name"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Get ranked placement skills for a department.

    Returns skills sorted by rating or name, optionally filtered by category.
    If the user is authenticated, their tracked skills are included.
    """
    dept = department.upper()
    if dept not in DEPARTMENT_KEYS:
        raise HTTPException(status_code=404, detail="Department not found")

    svc = SkillsService(db)
    data = await svc.get_skills(dept, category=category, sort_by=sort_by)
    if data is None:
        raise HTTPException(status_code=404, detail="No skill data for this department")

    # Include user's tracked skills if logged in
    if current_user:
        data["tracked_skills"] = await svc.get_tracked_skills(current_user)
    else:
        data["tracked_skills"] = []

    return data


@router.post(
    "/track",
    summary="Track a skill",
    description="Adds a skill to the authenticated user's learning/tracking list.",
    responses={
        200: {"description": "Updated list of tracked skills"},
        401: {"description": "Not authenticated"},
    },
)
async def track_skill(
    body: TrackSkillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Track a skill by adding it to the user's learning list.

    Returns the user's complete updated list of tracked skills.
    """
    svc = SkillsService(db)
    badges = await svc.track_skill(current_user, body.skill_name)
    return {"tracked_skills": badges}


@router.delete(
    "/track",
    summary="Untrack a skill",
    description="Removes a skill from the authenticated user's learning/tracking list.",
    responses={
        200: {"description": "Updated list of tracked skills"},
        401: {"description": "Not authenticated"},
    },
)
async def untrack_skill(
    body: TrackSkillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Untrack a skill by removing it from the user's learning list.

    Returns the user's complete updated list of tracked skills.
    """
    svc = SkillsService(db)
    badges = await svc.untrack_skill(current_user, body.skill_name)
    return {"tracked_skills": badges}


@router.get(
    "/tracking/me",
    summary="Get my tracked skills",
    description="Returns the list of skills the authenticated user is currently tracking.",
    responses={
        200: {"description": "List of tracked skills"},
        401: {"description": "Not authenticated"},
    },
)
async def get_my_tracked_skills(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get the current user's tracked skills.

    Returns the complete list of skills the user has added to their learning list.
    """
    svc = SkillsService(db)
    return {"tracked_skills": await svc.get_tracked_skills(current_user)}
