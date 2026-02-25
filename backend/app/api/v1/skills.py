"""API endpoints for placement skill rankings."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_optional_current_user
from app.departments import DEPARTMENT_KEYS
from app.models import User
from app.services.skills_service import SkillsService

router = APIRouter()


class TrackSkillRequest(BaseModel):
    skill_name: str


@router.get("/departments")
async def list_skill_departments():
    """List departments that have skill data."""
    return {"departments": SkillsService.get_available_departments()}


@router.get("/{department}")
async def get_skills(
    department: str,
    category: Optional[str] = Query(None, regex="^(core|tool|soft)$"),
    sort_by: str = Query("rating", regex="^(rating|name)$"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Get ranked skills for a department."""
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


@router.post("/track")
async def track_skill(
    body: TrackSkillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Track a skill (add to user's learning list)."""
    svc = SkillsService(db)
    badges = await svc.track_skill(current_user, body.skill_name)
    return {"tracked_skills": badges}


@router.delete("/track")
async def untrack_skill(
    body: TrackSkillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Untrack a skill (remove from user's learning list)."""
    svc = SkillsService(db)
    badges = await svc.untrack_skill(current_user, body.skill_name)
    return {"tracked_skills": badges}


@router.get("/tracking/me")
async def get_my_tracked_skills(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get the current user's tracked skills."""
    svc = SkillsService(db)
    return {"tracked_skills": await svc.get_tracked_skills(current_user)}
