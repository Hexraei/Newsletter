"""API endpoints for department listing and user department selection."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.departments import DEPARTMENTS, DEPARTMENT_KEYS, DEPARTMENT_SOURCES
from app.models import User

router = APIRouter()


class SetDepartmentRequest(BaseModel):
    department_key: str


@router.get(
    "/",
    summary="List all departments",
    description="Returns all available academic departments with their names, icons, descriptions, and content source counts.",
    responses={200: {"description": "List of all departments"}},
)
async def list_departments():
    """List all available departments.

    Returns department key, name, icon, description, and the total
    number of content sources configured for each department.
    """
    return {
        "departments": [
            {
                "key": d["key"],
                "name": d["name"],
                "icon": d["icon"],
                "description": d["description"],
                "source_count": (
                    len(DEPARTMENT_SOURCES.get(d["key"], {}).get("reddit", []))
                    + len(DEPARTMENT_SOURCES.get(d["key"], {}).get("rss", []))
                    + len(DEPARTMENT_SOURCES.get(d["key"], {}).get("medium", []))
                    + len(DEPARTMENT_SOURCES.get(d["key"], {}).get("youtube", []))
                ),
            }
            for d in DEPARTMENTS
        ]
    }


@router.get(
    "/{dept_key}",
    summary="Get department details",
    description="Returns detailed information about a specific department including its content source counts by type.",
    responses={
        200: {"description": "Department details with source counts"},
        404: {"description": "Department not found"},
    },
)
async def get_department(
    dept_key: str = Path(description="Department key (e.g., CSE, IT, AIDS, ECE, MECH, CIVIL)"),
):
    """Get details for a single department including source counts.

    Returns the department's name, icon, description, and a breakdown
    of content sources by type (Reddit, RSS, Medium, YouTube).
    """
    dept_key = dept_key.upper()
    if dept_key not in DEPARTMENT_KEYS:
        raise HTTPException(status_code=404, detail="Department not found")

    dept = next(d for d in DEPARTMENTS if d["key"] == dept_key)
    sources = DEPARTMENT_SOURCES.get(dept_key, {})
    return {
        **dept,
        "sources": {
            "reddit_count": len(sources.get("reddit", [])),
            "rss_count": len(sources.get("rss", [])),
            "medium_count": len(sources.get("medium", [])),
            "youtube_count": len(sources.get("youtube", [])),
        },
    }


@router.put(
    "/me",
    summary="Set user department",
    description="Sets the authenticated user's department preference, which affects personalized content recommendations.",
    responses={
        200: {"description": "Department updated successfully"},
        400: {"description": "Invalid department key"},
        401: {"description": "Not authenticated"},
    },
)
async def set_user_department(
    body: SetDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Set the authenticated user's department.

    Updates the user's department key and name. Affects which content
    appears in their personalized feed.
    """
    key = body.department_key.upper()
    if key not in DEPARTMENT_KEYS:
        raise HTTPException(status_code=400, detail="Invalid department key")

    current_user.department_key = key
    current_user.department = next(d["name"] for d in DEPARTMENTS if d["key"] == key)
    await db.commit()
    return {"message": "Department updated", "department_key": key}
