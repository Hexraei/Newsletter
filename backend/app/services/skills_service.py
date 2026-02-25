"""Service for placement skill rankings per department."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.skill_baselines import SKILL_BASELINES
from app.models.skills import SkillRanking


class SkillsService:
    """Cache-first service: DB cache → baseline data fallback."""

    CACHE_TTL_DAYS = 7

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_skills(
        self,
        department: str,
        category: Optional[str] = None,
        sort_by: str = "rating",
    ) -> Dict:
        """Return skill rankings for a department.

        1. Check DB cache (within TTL)
        2. Fall back to SKILL_BASELINES
        3. Seed DB cache from baseline on first access
        """
        dept = department.upper()
        now = datetime.now(timezone.utc)

        # 1. Try DB cache
        result = await self.db.execute(
            select(SkillRanking)
            .where(SkillRanking.department == dept)
            .where(SkillRanking.expires_at > now)
            .order_by(SkillRanking.generated_at.desc())
            .limit(1)
        )
        cached = result.scalar_one_or_none()

        if cached:
            skills = cached.skills
            summary = cached.summary
            sources = cached.sources
            methodology = cached.methodology
        else:
            # 2. Baseline fallback
            baseline = SKILL_BASELINES.get(dept)
            if not baseline:
                return None

            skills = baseline["skills"]
            summary = baseline["summary"]
            sources = baseline["sources"]
            methodology = baseline["methodology"]

            # 3. Seed cache
            await self._seed_cache(dept, baseline, now)

        # Apply filters
        if category:
            skills = [s for s in skills if s.get("category") == category]

        # Sort
        if sort_by == "rating":
            skills = sorted(skills, key=lambda s: s.get("rating", 0), reverse=True)
        elif sort_by == "name":
            skills = sorted(skills, key=lambda s: s.get("name", ""))

        return {
            "department": dept,
            "summary": summary,
            "skills": skills,
            "total_skills": len(skills),
            "sources": sources,
            "methodology": methodology,
            "last_updated": now.isoformat(),
        }

    async def _seed_cache(
        self, dept: str, baseline: Dict, now: datetime
    ) -> None:
        """Write baseline data into DB cache."""
        try:
            record = SkillRanking(
                department=dept,
                version=1,
                generated_at=now,
                expires_at=now + timedelta(days=self.CACHE_TTL_DAYS),
                summary=baseline["summary"],
                skills=baseline["skills"],
                sources=[{"name": s["name"], "url": s["url"]} for s in baseline["sources"]],
                methodology=baseline["methodology"],
                ai_model_used="baseline_v1",
            )
            self.db.add(record)
            await self.db.commit()
        except Exception:
            await self.db.rollback()

    async def track_skill(
        self, user, skill_name: str
    ) -> List[str]:
        """Add a skill to the user's tracked list."""
        badges = list(user.skill_badges or [])
        if skill_name not in badges:
            badges.append(skill_name)
            user.skill_badges = badges
            await self.db.commit()
        return badges

    async def untrack_skill(
        self, user, skill_name: str
    ) -> List[str]:
        """Remove a skill from the user's tracked list."""
        badges = list(user.skill_badges or [])
        if skill_name in badges:
            badges.remove(skill_name)
            user.skill_badges = badges
            await self.db.commit()
        return badges

    async def get_tracked_skills(self, user) -> List[str]:
        """Return the user's tracked skill list."""
        return list(user.skill_badges or [])

    @staticmethod
    def get_available_departments() -> List[str]:
        """Return department keys that have baseline data."""
        return sorted(SKILL_BASELINES.keys())
