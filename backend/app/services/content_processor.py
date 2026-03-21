"""Content processing service for transforming raw to processed content."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.ai_provider import AIProvider
from app.models import ProcessedContent, RawContent, Source
from app.models.base import AsyncSessionLocal
from app.services.cache_service import invalidate_feed_caches
from app.services.dept_relevance import (
    GENERAL_SOURCE_TYPES,
    assign_departments,
    detect_category,
    score_article_departments,
)

logger = logging.getLogger(__name__)
_IS_SQLITE = str(getattr(settings, "DATABASE_URL", "")).startswith("sqlite")


class ContentProcessor:
    """Process raw scraped content into newsletter-ready format."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_provider = AIProvider()
        self._image_fetchers: dict[tuple[str, ...], object] = {}
    
    # ── Source Reputation Tiers ─────────────────────────────────────────
    # Named sources get tiered scores based on editorial quality and
    # relevance to engineering students. This replaces the flat platform bonus.
    SOURCE_REPUTATION = {
        # Tier 1 (25 pts) — Top academic, govt research, premier institutions
        "IEEE Spectrum": 25, "ACM TechNews": 25, "ISRO News": 25,
        "ArXiv CS": 25, "ArXiv AI": 25, "ArXiv ML": 25, "ArXiv CV": 25,
        "ArXiv NLP": 25, "ArXiv Robotics": 25, "ArXiv Signal Processing": 25,
        "ArXiv Systems": 25, "ArXiv Systems & Control": 25,
        "ArXiv Quantitative Biology": 25, "ArXiv Chemical Physics": 25,
        "ArXiv Astrophysics": 25, "ArXiv Space Physics": 25,
        "ArXiv Fluid Dynamics": 25, "ArXiv Geophysics": 25,
        "ArXiv Materials Science": 25, "ArXiv Applied Physics": 25,
        "ArXiv Human-Robot Interaction": 25,
        "Science Robotics": 25, "Papers With Code": 25,
        "Google AI Blog": 25, "Microsoft Research": 25, "OpenAI Blog": 25,
        "NASA Blog": 25, "IIT Madras News": 25, "DST India": 25,
        "CSIR News": 25, "Vigyan Prasar": 25, "DRDO News": 25,
        "NIST News": 25, "ASCE News": 25, "SAE International": 25,
        # Tier 2 (20 pts) — Reputed tech media, Indian career/education, govt
        "TechCrunch": 20, "Ars Technica": 20, "MIT Tech Review AI": 20,
        "The Hindu Sci-Tech": 20, "The Hindu Education": 20,
        "Indian Express Technology": 20, "Economic Times Tech": 20,
        "NPTEL Announcements": 20, "NASSCOM Blog": 20,
        "Internshala Blog": 20, "Freshersworld Blog": 20,
        "Analytics Vidhya Blog": 20, "Electronics For You": 20,
        "PIB India": 20, "ET Govt": 20, "Hugging Face Blog": 20,
        "NVIDIA Robotics Blog": 20, "VentureBeat AI": 20,
        "Krebs on Security": 20, "InfoQ": 20, "Devfolio Blog": 20,
        "Unstop Blog": 20, "The News Minute Tech": 20,
        "TOI Education": 20, "Naukri Blog": 20,
        "ETAuto": 20, "ETEnergyWorld": 20, "ETInfra": 20,
        "ET CIO": 20, "ETTelecom": 20,
        # Tier 3 (15 pts) — Quality blogs, Indian startup/tech, niche industry
        "Dev.to": 15, "GeeksforGeeks Jobs": 15, "GeeksforGeeks": 15,
        "YourStory": 15, "Inc42": 15, "MediaNama": 15, "Trak.in": 15,
        "The Wire Science": 15, "Livemint Technology": 15,
        "The Verge": 15, "ZDNet": 15, "Bleeping Computer": 15,
        "Dark Reading": 15, "Hackaday": 15, "EE Times": 15,
        "Citizen Matters Bengaluru": 15, "Citizen Matters Chennai": 15,
        "Manufacturing Today India": 15, "BioVoice News": 15,
        "Mercom India Solar": 15, "The Robot Report": 15,
        "Boston Dynamics Blog": 15, "GEN News": 15, "STAT News": 15,
        "SpaceNews": 15, "AWS Blog": 15, "Google Cloud Blog": 15,
        "Renewable Energy World": 15, "Construction Dive": 15,
        "3D Printing Industry": 15, "Engineering.com": 15,
        "Waymo Blog": 20, "Figure AI Blog": 15,
        "Agility Robotics Blog": 15, "A3 Automate News": 15,
        "Robohub": 15, "Mobile Robot Guide": 15,
        "Clearpath Robotics Blog": 15, "Franka Robotics Blog": 15,
        "Yaskawa News": 15, "Omron Automation Blog": 15,
        "Nuro Blog": 15,
        # Tier 4 (10 pts) — General platforms, community sources
        "Hacker News": 10, "Reddit": 10, "Medium": 10, "Product Hunt": 10,
        "GitHub Trending": 10,
    }
    # Fallback by platform for sources not in the named dict
    PLATFORM_TIER_FALLBACK = {
        "research": 20, "rss": 8, "hackernews": 10, "github": 10,
        "reddit": 7, "medium": 7, "producthunt": 7,
    }

    # Locality keywords — presence in title/content triggers multiplier
    LOCALITY_KEYWORDS = {
        "chennai", "tamil nadu", "bangalore", "bengaluru", "hyderabad",
        "coimbatore", "madurai", "kochi", "trivandrum", "mysore",
        "srm university", "srm", "anna university", "vit", "iit madras",
        "iit hyderabad", "nit trichy", "psg tech", "iiitdm", "sastra",
        "bits pilani hyderabad", "iiit bangalore",
    }

    # Career-impact keywords — detect signals useful for student growth
    CAREER_DIRECT = {
        # Each keyword worth 5 pts (max 10 from this tier)
        "hiring", "recruitment", "fresher", "freshers", "internship",
        "campus placement", "walk-in", "job opening", "careers page",
        "salary", "compensation", "lpa", "ctc", "package",
        "workshop", "bootcamp", "certification", "training program",
        "free course", "scholarship", "fellowship",
    }
    CAREER_LEARNING = {
        # Each keyword worth 3 pts (max 9 from this tier)
        "tutorial", "hands-on", "getting started", "how to build",
        "project idea", "open source", "open-source",
        "skill demand", "trending skill", "must-learn", "roadmap",
        "breakthrough", "first-ever", "world record", "patent", "launched",
    }
    CAREER_TREND = {
        # Each keyword worth 2 pts (max 6 from this tier)
        "funding", "acquisition", "ipo", "valuation", "series a",
        "series b", "series c", "partnership", "collaboration",
        "mou", "contract awarded", "expansion", "new factory",
        "new facility", "production line",
    }

    INDIA_GEO_KEYWORDS = {
        "india", "indian", "bharat", "tamil nadu", "tamilnadu", "chennai", "coimbatore",
        "madurai", "trichy", "salem", "tirunelveli", "bangalore", "bengaluru", "hyderabad",
        "pune", "mumbai", "delhi", "noida", "gurgaon", "iit", "nit", "anna university",
        "srm", "vit", "bits pilani", "upsc", "jee", "gate", "ugc", "aicte", "nptel",
        "internshala", "freshersworld", "naukri",
    }
    INDIA_SOURCE_HINTS = {
        "times of india", "the hindu", "indian express", "livemint", "medianama", "inc42",
        "yourstory", "news18", "moneycontrol", "pib india", "et govt", "iit madras",
        "dst india", "csir", "nptel", "the news minute", "citizen matters",
    }
    INDIA_REDDIT_HINTS = {
        "r/developersindia",
        "r/indian_academia",
        "r/btechtards",
        "r/gate",
        "r/tamilnadu",
        "r/chennai",
    }
    ACTIONABILITY_KEYWORDS = {
        "internship", "intern", "placement", "hiring", "job", "fresher", "walk-in", "off-campus",
        "campus drive", "exam", "gate", "jee", "upsc", "scholarship", "fellowship", "deadline",
        "apply", "application", "registration", "eligibility", "course", "certification", "bootcamp",
        "hackathon", "challenge", "workshop", "career", "salary", "ctc",
        "recruitment", "vacancy", "notification", "last date", "admit card", "counselling",
        "campus hiring", "drive", "assessment", "test series", "results", "cutoff",
        "stipend", "apprentice", "apprenticeship", "walk in", "job fair",
    }
    KNOWLEDGE_KEYWORDS = {
        "research", "paper", "journal", "conference", "study",
        "ieee", "acm", "arxiv", "preprint", "publication",
        "breakthrough", "new model", "algorithm", "framework",
        "chip", "semiconductor", "vlsi", "embedded", "fpga",
        "robotics", "automation", "control system", "sensor",
        "battery", "renewable", "aerospace", "avionics",
        "biotech", "genomics", "materials", "manufacturing",
        "industry 4.0", "digital twin", "simulation", "protocol",
        "standard", "benchmark", "dataset", "inference", "training",
    }
    NOISE_PATTERNS = (
        "i will not promote",
        "upvote if",
        "please subscribe",
        "my channel",
        "rate my",
        "roast my",
        "thoughts?",
        "is this good?",
        "what do you think of my",
    )

    async def calculate_attractiveness_score(self, raw: RawContent) -> int:
        """Calculate attractiveness score (0-100) for content.

        Uses source reputation tiers, capped engagement, freshness,
        content quality, and locality multipliers to prioritize content
        relevant to South Indian engineering students.
        """
        score = 0

        # Base score
        score += 15

        # ── Engagement bonus (capped at 15 total) ──
        engagement = raw.raw_metadata.get("engagement", {}) if raw.raw_metadata else {}
        engagement_pts = 0
        if engagement:
            upvotes = engagement.get("upvotes", 0)
            if upvotes > 500:
                engagement_pts += 10
            elif upvotes > 100:
                engagement_pts += 7
            elif upvotes > 50:
                engagement_pts += 4
            stars = engagement.get("stars", 0)
            if stars > 1000:
                engagement_pts += 10
            elif stars > 500:
                engagement_pts += 7
            elif stars > 100:
                engagement_pts += 4
        score += min(15, engagement_pts)

        # ── Freshness bonus (max 20) ──
        if raw.published_at:
            try:
                published = raw.published_at
                now = datetime.now(timezone.utc)
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                age_hours = (now - published).total_seconds() / 3600
                if age_hours < 12:
                    score += 20
                elif age_hours < 24:
                    score += 16
                elif age_hours < 48:
                    score += 10
                elif age_hours < 72:
                    score += 5
            except Exception:
                pass

        # ── Content length bonus (max 15) ──
        content_length = len(raw.original_content or "")
        if content_length > 2000:
            score += 15
        elif content_length > 1000:
            score += 12
        elif content_length > 500:
            score += 8
        elif content_length > 200:
            score += 4

        # ── Source reputation tier (replaces flat platform bonus) ──
        source_result = await self.db.execute(
            select(Source).where(Source.id == raw.source_id)
        )
        source = source_result.scalar_one_or_none()
        source_name = source.name if source else ""
        source_type = source.source_type if source else ""
        platform = source.platform if source else ""

        # Named source lookup → platform fallback → 5 (unknown)
        reputation_pts = self.SOURCE_REPUTATION.get(
            source_name,
            self.PLATFORM_TIER_FALLBACK.get(platform, 5)
        )
        score += reputation_pts

        # India source type bonus (stacks with reputation)
        india_type_bonus = {
            "india-news": 4, "india-tech": 5, "india-startup": 4,
            "india-education": 6, "india-career": 8, "india-policy": 3,
            "india-industry": 4, "india-energy": 4, "india-defence": 3,
            "india-south": 8, "india-research": 7, "india-events": 8,
        }
        score += india_type_bonus.get(source_type, 0)

        # ── Career-impact scoring (max 15 pts) ──
        text = ((raw.original_title or "") + " " + (raw.original_content or "")[:2000]).lower()

        direct_pts = sum(5 for kw in self.CAREER_DIRECT if kw in text)
        learning_pts = sum(3 for kw in self.CAREER_LEARNING if kw in text)
        trend_pts = sum(2 for kw in self.CAREER_TREND if kw in text)
        career_pts = min(10, direct_pts) + min(9, learning_pts) + min(6, trend_pts)
        score += min(15, career_pts)

        # ── Locality multiplier ──
        locality_hits = sum(1 for kw in self.LOCALITY_KEYWORDS if kw in text)
        if locality_hits >= 3:
            score = int(score * 1.35)
        elif locality_hits >= 1:
            score = int(score * 1.2)

        # Career/opportunity source type boost
        if source_type in ("india-career", "india-events"):
            score = int(score * 1.15)

        return min(100, score)
    
    async def process_pending_items(
        self,
        limit: int = 10,
        mode: str = "quality",
        concurrency: int = 1,
        progress_every: int = 10,
    ) -> Dict:
        """Process pending raw content items."""
        mode = (mode or "quality").lower()
        if mode not in {"speed", "balanced", "quality", "india_strict"}:
            mode = "quality"

        include_semantic_images = mode != "speed"
        worker_count = max(1, int(concurrency or 1))
        if worker_count > 1 and settings.DATABASE_URL.startswith("sqlite"):
            logger.info("SQLite backend detected; using single-worker processing for DB safety.")
            worker_count = 1

        # Get pending items
        result = await self.db.execute(
            select(RawContent)
            .where(RawContent.status == "pending")
            .order_by(RawContent.scraped_at.desc())
            .limit(limit)
        )
        pending_items = result.scalars().all()

        if not pending_items:
            return {
                "processed": 0,
                "total_pending": 0,
                "errors": [],
                "rejected": 0,
                "rejected_samples": [],
                "runtime_failed": 0,
                "mode": mode,
                "concurrency": worker_count,
                "ai_enriched": 0,
                "basic_processed": 0,
            }

        score_cache: Dict[str, int] = {}
        ai_allowed_ids = set()
        if mode == "balanced":
            ai_allowed_ids, score_cache = await self._plan_balanced_ai_budget(pending_items)

        processed_count = 0
        ai_processed_count = 0
        errors = []
        rejected_samples = []
        rejected_count = 0
        runtime_failed_count = 0
        strict_yield_by_source: dict[str, dict[str, Any]] = {}
        pending_by_id = {raw.id: raw for raw in pending_items}
        source_map = await self._load_sources_for_items(pending_items)

        def _metric_bucket(raw: RawContent) -> dict[str, Any]:
            source = source_map.get(raw.source_id)
            key = str(raw.source_id)
            if key not in strict_yield_by_source:
                strict_yield_by_source[key] = {
                    "source_id": raw.source_id,
                    "source_name": source.name if source else f"source-{raw.source_id}",
                    "platform": (source.platform if source else "") or "unknown",
                    "source_type": (source.source_type if source else "") or "unknown",
                    "attempted": 0,
                    "passed": 0,
                    "rejected": 0,
                    "runtime_failed": 0,
                    "strict_rejected": 0,
                    "noise_rejected": 0,
                }
            return strict_yield_by_source[key]

        def _record_source_outcome(raw: RawContent, success: bool, error_text: str = "") -> None:
            bucket = _metric_bucket(raw)
            bucket["attempted"] += 1
            if success:
                bucket["passed"] += 1
                return
            error_lower = error_text.lower()
            if "strict relevance gate failed" in error_lower:
                bucket["rejected"] += 1
                bucket["strict_rejected"] += 1
            elif "noise filter" in error_lower:
                bucket["rejected"] += 1
                bucket["noise_rejected"] += 1
            else:
                bucket["runtime_failed"] += 1

        if worker_count == 1:
            for idx, raw in enumerate(pending_items, start=1):
                force_basic = mode == "speed" or (mode == "balanced" and raw.id not in ai_allowed_ids)
                try:
                    await self.process_single_item(
                        raw,
                        source=source_map.get(raw.source_id),
                        force_basic=force_basic,
                        include_semantic_images=include_semantic_images,
                        precomputed_score=score_cache.get(raw.id),
                    )
                    processed_count += 1
                    if not force_basic:
                        ai_processed_count += 1
                    _record_source_outcome(raw, success=True)
                except Exception as e:
                    error_text = str(e)
                    status = self._classify_failure_status(error_text)
                    _record_source_outcome(raw, success=False, error_text=error_text)
                    if status == "rejected":
                        rejected_count += 1
                        if len(rejected_samples) < 25:
                            rejected_samples.append(f"{raw.id}: {error_text}")
                    else:
                        runtime_failed_count += 1
                        errors.append(f"Error processing {raw.id}: {error_text}")
                    raw.status = status
                    raw.processing_error = error_text[:500]
                    await self.db.commit()

                if progress_every > 0 and (idx % progress_every == 0 or idx == len(pending_items)):
                    logger.info(
                        "Processing progress: %d/%d complete (mode=%s, ai=%d, basic=%d)",
                        idx,
                        len(pending_items),
                        mode,
                        ai_processed_count,
                        processed_count - ai_processed_count,
                    )
        else:
            pending_ids = [raw.id for raw in pending_items]
            progress = {"done": 0}
            progress_lock = asyncio.Lock()
            semaphore = asyncio.Semaphore(worker_count)

            async def _process_with_worker(raw_id: str) -> tuple[bool, bool, str, str]:
                async with semaphore:
                    async with AsyncSessionLocal() as worker_db:
                        worker_processor = ContentProcessor(worker_db)
                        raw = await worker_db.get(RawContent, raw_id)
                        if not raw or raw.status != "pending":
                            return False, False, "", ""

                        force_basic = mode == "speed" or (mode == "balanced" and raw_id not in ai_allowed_ids)
                        try:
                            await worker_processor.process_single_item(
                                raw,
                                force_basic=force_basic,
                                include_semantic_images=include_semantic_images,
                                precomputed_score=score_cache.get(raw_id),
                            )
                            return True, not force_basic, "", ""
                        except Exception as exc:
                            error_text = str(exc)
                            status = worker_processor._classify_failure_status(error_text)
                            raw.status = status
                            raw.processing_error = error_text[:500]
                            await worker_db.commit()
                            return False, False, error_text, status
                        finally:
                            async with progress_lock:
                                progress["done"] += 1
                                if progress_every > 0 and (
                                    progress["done"] % progress_every == 0 or progress["done"] == len(pending_ids)
                                ):
                                    logger.info(
                                        "Processing progress: %d/%d complete (mode=%s)",
                                        progress["done"],
                                        len(pending_ids),
                                        mode,
                                    )

            results = await asyncio.gather(*[_process_with_worker(raw_id) for raw_id in pending_ids])
            for raw_id, (success, used_ai, error_text, status) in zip(pending_ids, results):
                raw = pending_by_id.get(raw_id)
                if raw:
                    _record_source_outcome(raw, success=success, error_text=error_text)
                if success:
                    processed_count += 1
                    if used_ai:
                        ai_processed_count += 1
                elif error_text:
                    if status == "rejected":
                        rejected_count += 1
                        if len(rejected_samples) < 25:
                            rejected_samples.append(f"{raw_id}: {error_text}")
                    else:
                        runtime_failed_count += 1
                        errors.append(f"Error processing {raw_id}: {error_text}")

        # Invalidate feed caches when new content is processed
        if processed_count > 0:
            try:
                await invalidate_feed_caches()
                logger.info("Feed caches invalidated after processing %d items", processed_count)
            except Exception:
                logger.warning("Failed to invalidate feed caches", exc_info=True)
        
        strict_source_rows = []
        for row in strict_yield_by_source.values():
            attempted = row["attempted"] or 0
            row["pass_rate"] = round((row["passed"] / attempted) * 100, 2) if attempted else 0.0
            strict_source_rows.append(row)
        strict_source_rows.sort(key=lambda item: item["attempted"], reverse=True)

        return {
            "processed": processed_count,
            "total_pending": len(pending_items),
            "errors": errors,
            "rejected": rejected_count,
            "rejected_samples": rejected_samples,
            "runtime_failed": runtime_failed_count,
            "mode": mode,
            "concurrency": worker_count,
            "ai_enriched": ai_processed_count,
            "basic_processed": processed_count - ai_processed_count,
            "strict_yield_by_source": strict_source_rows,
        }

    async def _plan_balanced_ai_budget(self, pending_items: List[RawContent]) -> tuple[set[str], Dict[str, int]]:
        """Pick a capped subset for AI enrichment in balanced mode."""
        score_cache: Dict[str, int] = {}
        scored_items: list[tuple[float, str]] = []

        for raw in pending_items:
            score = await self.calculate_attractiveness_score(raw)
            score_cache[raw.id] = score
            age_hours = self._content_age_hours(raw)
            freshness_bonus = 24 if age_hours is None else max(0.0, 24.0 - min(age_hours, 24.0))
            priority = score + freshness_bonus
            scored_items.append((priority, raw.id))

        quota = min(len(scored_items), max(8, min(30, len(scored_items) // 2)))
        scored_items.sort(reverse=True)
        allowed_ids = {item_id for _, item_id in scored_items[:quota]}
        return allowed_ids, score_cache

    async def process_single_item(
        self,
        raw: RawContent,
        *,
        source: Optional[Source] = None,
        force_basic: bool = False,
        include_semantic_images: bool = True,
        precomputed_score: Optional[int] = None,
    ) -> Optional[ProcessedContent]:
        """Process a single raw content item."""

        # Calculate attractiveness score
        attractiveness_score = precomputed_score if precomputed_score is not None else await self.calculate_attractiveness_score(raw)
        source = source or await self._get_source(raw.source_id)

        prefilter_ok, geo_score, actionability_score, knowledge_score = self._strict_prefilter_decision(raw, source)
        if (
            settings.RELEVANCE_STRICT_MODE
            and getattr(settings, "RELEVANCE_PREFILTER_ENABLED", True)
            and not prefilter_ok
        ):
            raw.status = "rejected"
            raw.processing_error = (
                "Strict relevance gate failed "
                f"(geo={geo_score}, actionability={actionability_score}, knowledge={knowledge_score})"
            )
            raw.processed_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise ValueError(raw.processing_error)

        if self._is_noise_content(raw):
            raw.status = "rejected"
            raw.processing_error = "Rejected by strict relevance noise filter"
            raw.processed_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise ValueError(raw.processing_error)

        if force_basic:
            processed = await self._process_basic(
                raw,
                source=source,
                score=attractiveness_score,
                include_semantic_images=include_semantic_images,
                geo_score=geo_score,
                actionability_score=actionability_score,
                knowledge_score=knowledge_score,
            )
        else:
            processed = await self._process_with_nlp(
                raw,
                source=source,
                score=attractiveness_score,
                include_semantic_images=include_semantic_images,
                geo_score=geo_score,
                actionability_score=actionability_score,
                knowledge_score=knowledge_score,
            )

        # Update raw content status
        raw.status = "processed"
        raw.processed_at = datetime.now(timezone.utc)
        await self.db.commit()

        return processed

    async def _get_source(self, source_id: int) -> Optional[Source]:
        result = await self.db.execute(select(Source).where(Source.id == source_id))
        return result.scalar_one_or_none()

    async def _load_sources_for_items(self, items: List[RawContent]) -> dict[int, Source]:
        source_ids = {raw.source_id for raw in items if raw.source_id is not None}
        source_map: dict[int, Source] = {}
        if not source_ids:
            return source_map
        result = await self.db.execute(select(Source).where(Source.id.in_(source_ids)))
        for source in result.scalars().all():
            source_map[source.id] = source
        return source_map

    def _resolve_publish_time(self, raw: RawContent) -> datetime:
        dt = raw.published_at or raw.scraped_at
        if dt is None:
            return datetime.now(timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _source_text(self, raw: RawContent, source: Optional[Source]) -> str:
        metadata = raw.raw_metadata or {}
        bits = [
            raw.original_title or "",
            raw.original_content or "",
            raw.original_url or "",
            metadata.get("feed_name", ""),
            metadata.get("feed_type", ""),
            source.name if source else "",
            source.source_type if source else "",
            source.platform if source else "",
        ]
        return " ".join(str(x) for x in bits if x).lower()

    def _geo_relevance_score(self, raw: RawContent, source: Optional[Source]) -> int:
        text = self._source_text(raw, source)
        score = 0
        hits = sum(1 for kw in self.INDIA_GEO_KEYWORDS if kw in text)
        score += min(70, hits * 12)
        src_hits = sum(1 for kw in self.INDIA_SOURCE_HINTS if kw in text)
        score += min(25, src_hits * 8)
        if source and str(source.source_type or "").startswith("india-"):
            # Curated india-* sources should satisfy geo baseline; actionability still gates publish.
            score = max(score, 70)
        if source and str(source.platform or "").lower() == "reddit":
            if any(hint in text for hint in self.INDIA_REDDIT_HINTS):
                # India student-focused subreddits are geo-relevant by definition.
                score = max(score, 60)
        return max(0, min(100, score))

    def _student_actionability_score(self, raw: RawContent) -> int:
        text = f"{raw.original_title or ''} {raw.original_content or ''}".lower()
        score = 0
        hits = sum(1 for kw in self.ACTIONABILITY_KEYWORDS if kw in text)
        score += min(80, hits * 12)
        if any(k in text for k in ("deadline", "apply", "registration", "eligibility")):
            score += 20
        return max(0, min(100, score))

    def _knowledge_relevance_score(self, raw: RawContent, source: Optional[Source]) -> int:
        text = self._source_text(raw, source)
        score = 0
        hits = sum(1 for kw in self.KNOWLEDGE_KEYWORDS if kw in text)
        score += min(75, hits * 9)
        if source and str(source.source_type or "").lower() in {"academic", "industry", "india-research", "india-tech"}:
            score += 20
        if source and str(source.platform or "").lower() == "research":
            score += 20
        return max(0, min(100, score))

    def _is_noise_content(self, raw: RawContent) -> bool:
        text = f"{raw.original_title or ''} {raw.original_content or ''}".lower()
        if any(p in text for p in self.NOISE_PATTERNS):
            return True
        title = (raw.original_title or "").strip().lower()
        if title.endswith("?") and len((raw.original_content or "").strip()) < 120:
            return True
        return False

    def _passes_strict_relevance_gate(
        self,
        raw: RawContent,
        source: Optional[Source],
    ) -> tuple[bool, int, int, int]:
        geo = self._geo_relevance_score(raw, source)
        actionability = self._student_actionability_score(raw)
        knowledge = self._knowledge_relevance_score(raw, source)
        min_geo = int(getattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45))
        min_actionability_default = int(getattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25))
        min_actionability_reddit = int(
            getattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE_REDDIT", min_actionability_default)
        )
        min_knowledge = int(getattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32))
        is_reddit = bool(source and str(source.platform or "").lower() == "reddit")
        min_actionability = min_actionability_reddit if is_reddit else min_actionability_default
        global_override = int(getattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65))
        global_knowledge_override = int(getattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72))
        passed = (
            (geo >= min_geo and actionability >= min_actionability)
            or (geo >= min_geo and knowledge >= min_knowledge)
            or actionability >= global_override
            or knowledge >= global_knowledge_override
        )
        return passed, geo, actionability, knowledge

    def _strict_prefilter_decision(
        self,
        raw: RawContent,
        source: Optional[Source],
    ) -> tuple[bool, int, int, int]:
        return self._passes_strict_relevance_gate(raw, source)

    def _classify_failure_status(self, error_text: str) -> str:
        """Map processing outcome to status without hiding runtime failures."""
        lowered = (error_text or "").lower()
        if "strict relevance gate failed" in lowered or "noise filter" in lowered:
            return "rejected"
        return "failed"

    def _normalize_raw_content_id(self, raw_id: Any) -> Optional[str]:
        """Normalize UUID-like IDs for stable joins across SQLite/Postgres."""
        if raw_id is None:
            return None
        normalized = str(raw_id).strip().lower()
        if _IS_SQLITE:
            normalized = normalized.replace("-", "")
        return normalized or None

    def _fallback_department_tags(
        self,
        source_tags: List[str],
        source_type: str,
    ) -> List[str]:
        """Fallback tags only for department-specific (non-general) sources."""
        if not source_tags:
            return ["general"]
        if source_type in GENERAL_SOURCE_TYPES:
            return ["general"]
        return source_tags

    async def _process_with_nlp(
        self,
        raw: RawContent,
        source: Optional[Source],
        score: int,
        *,
        include_semantic_images: bool = True,
        geo_score: Optional[int] = None,
        actionability_score: Optional[int] = None,
        knowledge_score: Optional[int] = None,
    ) -> ProcessedContent:
        """Process with full NLP (high attractiveness)."""
        
        # Get AI summary
        try:
            detected_cat = detect_category(raw.original_title or "", raw.original_content or "")
            summary_data = await self.ai_provider.summarize(
                title=raw.original_title or "",
                content=raw.original_content or "",
                category=detected_cat or "general"
            )
        except Exception as e:
            # Fallback to basic if AI fails
            import logging as _log
            _log.getLogger(__name__).warning("AI summarization failed: %s, using basic", e)
            return await self._process_basic(
                raw,
                source=source,
                score=score,
                include_semantic_images=include_semantic_images,
                geo_score=geo_score,
                actionability_score=actionability_score,
                knowledge_score=knowledge_score,
            )
        
        # Get source info for department tags
        source = source or await self._get_source(raw.source_id)
        source_name = source.name if source else ""
        
        # Determine department tags via content analysis (not just source tags)
        source_tags = (source.department_tags or source.default_categories) if source else []
        source_type = source.source_type if source else ""
        dept_tags = assign_departments(
            raw.original_title or "",
            raw.original_content or "",
            source_dept_tags=source_tags,
            source_type=source_type,
        )

        # Compute composite relevance_score (5-100) from multiple signals
        dept_scores = score_article_departments(
            raw.original_title or "",
            raw.original_content or "",
            source_dept_tags=source_tags,
            source_type=source_type,
        )
        max_dept_score = dept_scores[0][1] if dept_scores else 0
        # Content quality
        content_len = len(raw.original_content or "")
        _rel = 0
        if content_len >= 500: _rel += 15
        elif content_len >= 200: _rel += 10
        elif content_len >= 50: _rel += 5
        kp = summary_data.get("key_points", [])
        hook = summary_data.get("hook", "")
        if kp and len(kp) >= 2: _rel += 10
        if hook and hook != (raw.original_title or "") and len(hook) > 20: _rel += 5
        # Category specificity
        _cat = detect_category(raw.original_title or "", raw.original_content or "")
        if _cat and _cat != "general": _rel += 15
        else: _rel += 3
        # Career and opportunity content gets extra relevance
        if _cat in ("career", "opportunity"):
            _rel += 20  # High relevance for actionable career content
        # Department relevance
        _rel += min(35, int(max_dept_score * 3.5))
        # Source quality
        if score >= 50: _rel += 20
        elif score >= 40: _rel += 15
        elif score >= 30: _rel += 10
        elif score >= 20: _rel += 5
        relevance_score = max(5, min(100, _rel))

        # Determine if this is breaking news using quality + recency + urgency rules
        is_breaking = self._is_breaking_candidate(raw, score)
        breaking_score = self._calculate_breaking_score(raw, score) if is_breaking else None
        
        # Generate appropriate headline
        try:
            if is_breaking:
                # Use breaking news headline generator for urgent, impactful headlines
                headline = await self.ai_provider.breaking_headline(
                    title=raw.original_title or "",
                    content=raw.original_content or "",
                    source=source_name
                )
            else:
                # Use regular headline generator
                headline = await self.ai_provider.headline(
                    title=raw.original_title or "",
                    content=raw.original_content or ""
                )
        except Exception:
            import logging as _log
            _log.getLogger(__name__).warning("Headline generation failed, using original title", exc_info=True)
            headline = raw.original_title
        
        # Prefer Unsplash; fall back to source image or secondary providers.
        featured_image_url, image_credit = await self._resolve_featured_image(
            raw=raw,
            title=raw.original_title or "",
            category=detected_cat or "general",
            allow_semantic=include_semantic_images,
        )
        
        # Determine content type
        content_type = self._detect_content_type(raw, source)

        if geo_score is None or actionability_score is None or knowledge_score is None:
            _, geo_score, actionability_score, knowledge_score = self._passes_strict_relevance_gate(raw, source)

        base_visualizations = {
            "geo_relevance_score": geo_score,
            "student_actionability_score": actionability_score,
            "knowledge_relevance_score": knowledge_score,
        }
        if image_credit:
            base_visualizations["image_credit"] = image_credit

        # Create processed content
        processed = ProcessedContent(
            raw_content_id=self._normalize_raw_content_id(raw.id),
            title=headline or raw.original_title or "Untitled",
            summary=summary_data.get("why_it_matters", ""),
            content_blocks={
                "hook": summary_data.get("hook", ""),
                "why_it_matters": summary_data.get("why_it_matters", ""),
                "key_points": summary_data.get("key_points", []),
                "action_step": summary_data.get("action_step", "")
            },
            reading_time_minutes=2,
            category=detect_category(raw.original_title or "", raw.original_content or ""),
            department_tags=dept_tags if dept_tags else self._fallback_department_tags(source_tags, source_type),
            topic_tags=self._extract_topics(raw),
            attractiveness_score=score,
            relevance_score=relevance_score,
            quality_score=min(100, score + 10),
            content_type=content_type,
            status="published",
            published_at=self._resolve_publish_time(raw),
            is_breaking=is_breaking,
            breaking_score=breaking_score,
            breaking_detected_at=datetime.now(timezone.utc) if is_breaking else None,
            featured_image_url=featured_image_url,
            visualizations=base_visualizations,
        )
        
        self.db.add(processed)
        await self.db.commit()
        await self.db.refresh(processed)
        
        return processed
    
    async def _process_basic(
        self,
        raw: RawContent,
        source: Optional[Source],
        score: int,
        *,
        include_semantic_images: bool = True,
        geo_score: Optional[int] = None,
        actionability_score: Optional[int] = None,
        knowledge_score: Optional[int] = None,
    ) -> ProcessedContent:
        """Basic processing for low attractiveness (snippet only)."""
        
        # Get source info
        source = source or await self._get_source(raw.source_id)
        
        # Build a useful summary from available data
        title = raw.original_title or "Untitled"
        content = raw.original_content or ""
        metadata = raw.raw_metadata or {}
        engagement = metadata.get("engagement", {})

        # If content is just score info (e.g. "Score: 125 | Comments: 22"),
        # generate a better summary from the title and metadata
        is_score_only = content.startswith("Score:") or len(content) < 50
        if is_score_only:
            parts = []
            upvotes = engagement.get("upvotes", 0)
            comments = engagement.get("comments", 0)
            if upvotes:
                parts.append(f"{upvotes} upvotes")
            if comments:
                parts.append(f"{comments} comments")
            source_name = source.name if source else "the web"
            engagement_str = f" ({', '.join(parts)})" if parts else ""
            summary = f"Trending on {source_name}{engagement_str}. {title}."
        else:
            summary = content[:300]
            if len(content) > 300:
                summary += "..."

        # Even in basic mode, keep media and breaking metadata consistent.
        is_breaking = self._is_breaking_candidate(raw, score)
        breaking_score = self._calculate_breaking_score(raw, score) if is_breaking else None
        content_type = self._detect_content_type(raw, source)

        # For research papers, create a better summary
        if content_type == "research_paper":
            metadata = raw.raw_metadata or {}
            venue = metadata.get("venue", "")
            citations = metadata.get("citations", 0)
            authors = (raw.original_author or "")[:100]
            parts = []
            if authors:
                parts.append(f"By {authors}")
            if venue:
                parts.append(f"Published in {venue}")
            if citations:
                parts.append(f"{citations} citations")
            meta_line = " | ".join(parts)
            abstract = (raw.original_content or "")[:300]
            summary = f"{meta_line}. {abstract}" if meta_line else abstract

        basic_category = detect_category(title, content)
        featured_image_url, image_credit = await self._resolve_featured_image(
            raw=raw,
            title=title,
            category=basic_category,
            allow_semantic=include_semantic_images,
        )

        # Assign departments via content analysis
        source_tags = (source.department_tags or source.default_categories) if source else []
        source_type = source.source_type if source else ""
        dept_tags = assign_departments(
            title, content,
            source_dept_tags=source_tags,
            source_type=source_type,
        )

        # Compute composite relevance_score (5-100) from multiple signals
        dept_scores = score_article_departments(
            title, content,
            source_dept_tags=source_tags,
            source_type=source_type,
        )
        max_dept_score = dept_scores[0][1] if dept_scores else 0
        content_len = len(content)
        _rel = 0
        if content_len >= 500: _rel += 15
        elif content_len >= 200: _rel += 10
        elif content_len >= 50: _rel += 5
        _cat = detect_category(title, content)
        if _cat and _cat != "general": _rel += 15
        else: _rel += 3
        # Career and opportunity content gets extra relevance
        if _cat in ("career", "opportunity"):
            _rel += 20  # High relevance for actionable career content
        _rel += min(35, int(max_dept_score * 3.5))
        if score >= 50: _rel += 20
        elif score >= 40: _rel += 15
        elif score >= 30: _rel += 10
        elif score >= 20: _rel += 5
        relevance_score = max(5, min(100, _rel))

        if geo_score is None or actionability_score is None or knowledge_score is None:
            _, geo_score, actionability_score, knowledge_score = self._passes_strict_relevance_gate(raw, source)

        base_visualizations = {
            "geo_relevance_score": geo_score,
            "student_actionability_score": actionability_score,
            "knowledge_relevance_score": knowledge_score,
        }
        if image_credit:
            base_visualizations["image_credit"] = image_credit

        processed = ProcessedContent(
            raw_content_id=self._normalize_raw_content_id(raw.id),
            title=title,
            summary=summary,
            content_blocks={
                "hook": title,
                "why_it_matters": summary,
                "key_points": [],
            },
            reading_time_minutes=max(1, len(content) // 1000 + 1),
            category=basic_category,
            department_tags=dept_tags if dept_tags else self._fallback_department_tags(source_tags, source_type),
            topic_tags=self._extract_topics(raw),
            attractiveness_score=score,
            relevance_score=relevance_score,
            quality_score=score,
            content_type=content_type if content_type == "research_paper" else "snippet",
            status="published",
            published_at=self._resolve_publish_time(raw),
            is_breaking=is_breaking,
            breaking_score=breaking_score,
            breaking_detected_at=datetime.now(timezone.utc) if is_breaking else None,
            featured_image_url=featured_image_url,
            visualizations=base_visualizations,
        )
        
        self.db.add(processed)
        await self.db.commit()
        await self.db.refresh(processed)
        
        return processed

    def _content_age_hours(self, raw: RawContent) -> Optional[float]:
        """Get content age in hours from published/scraped timestamp."""
        dt = raw.published_at or raw.scraped_at
        if not dt:
            return None

        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return max(0.0, (now - dt).total_seconds() / 3600)

    def _has_urgent_keywords(self, raw: RawContent) -> bool:
        """Detect urgent/breaking signals in text using specific, high-signal event terms."""
        text = f"{raw.original_title or ''} {raw.original_content or ''}".lower()
        keywords = [
            "breaking",
            "just announced",
            "outage",
            "urgent",
            "security flaw",
            "data breach",
            "zero-day",
            "vulnerability",
            "exploit",
            "acquires",
            "banned",
            "lawsuit",
            "recall",
            "emergency",
            "shutdown",
            "offline",
            "hacked",
            "launch",
            "release",
            "unveils",
            "announces",
            "critical",
            "alert",
            "leaked",
            "disruption",
            "acquisition",
            "ipo",
            "layoff",
            "raises",
        ]
        return any(k in text for k in keywords)

    def _is_breaking_candidate(self, raw: RawContent, score: int) -> bool:
        """Decide if a story should be marked as breaking.

        Uses achievable score thresholds (max score ~55 from RSS feeds).
        """
        age_hours = self._content_age_hours(raw)
        if age_hours is None or age_hours > 48:
            return False

        # Tier 1: Top-scoring + recent
        if score >= 55 and age_hours <= 6:
            return True
        # Tier 2: Good score + very fresh
        if score >= 50 and age_hours <= 3:
            return True
        # Tier 3: Decent score + fresh + urgent keywords
        if score >= 45 and age_hours <= 6 and self._has_urgent_keywords(raw):
            return True

        return False

    def _calculate_breaking_score(self, raw: RawContent, score: int) -> int:
        """Calculate weighted breaking score for ranking."""
        age_hours = self._content_age_hours(raw)
        boost = 0

        if age_hours is not None:
            if age_hours <= 1:
                boost += 25
            elif age_hours <= 3:
                boost += 20
            elif age_hours <= 6:
                boost += 15
            elif age_hours <= 12:
                boost += 10
            elif age_hours <= 24:
                boost += 5

        if self._has_urgent_keywords(raw):
            boost += 10

        return min(100, score + boost)
    
    def _detect_content_type(self, raw: RawContent, source) -> str:
        """Detect if content is a research paper based on source and metadata."""
        metadata = raw.raw_metadata or {}
        # Explicitly tagged by scraper
        if metadata.get("content_type") == "research_paper":
            return "research_paper"
        # From research platform
        if source and source.platform == "research":
            return "research_paper"
        # ArXiv source
        url = (raw.original_url or "").lower()
        if "arxiv.org" in url:
            return "research_paper"
        return "news"

    def _detect_category(self, raw: RawContent) -> str:
        """Detect content category from metadata."""
        title = (raw.original_title or "").lower()
        content = (raw.original_content or "").lower()
        
        categories = {
            "ai_ml": ["ai", "machine learning", "gpt", "llm", "neural", "deep learning"],
            "webdev": ["javascript", "react", "vue", "angular", "frontend", "web"],
            "backend": ["python", "java", "go", "rust", "backend", "server"],
            "mobile": ["ios", "android", "flutter", "react native", "mobile"],
            "devops": ["docker", "kubernetes", "ci/cd", "aws", "cloud"],
            "career": ["job", "hiring", "interview", "salary", "career"],
            "startup": ["startup", "funding", "venture", "entrepreneur"],
            "security": ["security", "vulnerability", "hack", "cve", "exploit"],
        }
        
        scores = {}
        for cat, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in title or kw in content)
            if score > 0:
                scores[cat] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "general"
    
    def _extract_topics(self, raw: RawContent) -> List[str]:
        """Extract topic tags from content."""
        title = (raw.original_title or "").lower()
        
        # Common tech topics
        topics = []
        tech_keywords = [
            "python", "javascript", "typescript", "react", "vue", "angular",
            "nodejs", "django", "fastapi", "docker", "kubernetes", "aws",
            "ai", "machine learning", "openai", "gpt", "api", "database"
        ]
        
        for keyword in tech_keywords:
            if keyword in title:
                topics.append(keyword.replace(" ", "-"))
        
        return topics[:5]  # Max 5 topics
    
    def _extract_featured_image(self, raw: RawContent) -> Optional[str]:
        """Extract featured image URL from metadata.
        
        Checks for common Open Graph and Twitter Card image meta tags.
        """
        metadata = raw.raw_metadata or {}
        
        # Check for Open Graph image
        if "og_image" in metadata:
            return metadata["og_image"]
        if "og:image" in metadata:
            return metadata["og:image"]
        
        # Check for Twitter Card image
        if "twitter_image" in metadata:
            return metadata["twitter_image"]
        if "twitter:image" in metadata:
            return metadata["twitter:image"]
        if "twitter:image:src" in metadata:
            return metadata["twitter:image:src"]
        
        # Check for other common image fields
        if "image" in metadata:
            return metadata["image"]
        if "thumbnail" in metadata:
            return metadata["thumbnail"]
        if "featured_image" in metadata:
            return metadata["featured_image"]
        
        # Check in external_url metadata for Reddit/HN
        external_url = metadata.get("external_url", "")
        if external_url and ("youtube.com" in external_url or "youtu.be" in external_url):
            # YouTube videos - could extract thumbnail if needed
            pass
        
        return None

    async def _resolve_featured_image(
        self,
        raw: RawContent,
        title: str,
        category: str = "general",
        allow_semantic: bool = True,
    ) -> tuple[Optional[str], Optional[dict]]:
        """Resolve image URL with Unsplash-first policy.

        Order:
        1) Unsplash semantic match
        2) Existing source/OG image from scraped metadata
        3) Secondary semantic providers (Openverse/Wikimedia/Pixabay/Pexels)
        """
        source_image = self._extract_featured_image(raw)
        if not allow_semantic:
            return source_image, None

        semantic = await self._fetch_semantic_image(
            title=title,
            category=category,
            fallback_url=source_image,
        )
        if semantic and semantic.get("url"):
            return semantic["url"], semantic.get("credit")
        return source_image, None

    async def _fetch_semantic_image(
        self,
        title: Optional[str],
        category: str = "general",
        fallback_url: Optional[str] = None,
    ) -> Optional[dict]:
        """Fetch a semantically relevant image for the article title.
        
        Uses Unsplash first and only falls back to source/other providers if needed.
        Returns dict with 'url' and structured 'credit', or None.
        """
        if not title or len(title.strip()) < 5:
            return {"url": fallback_url, "credit": None} if fallback_url else None
        try:
            from app.services.image_fetcher import ImageFetcher
            primary_fetcher = self._get_image_fetcher(["unsplash"], ImageFetcher)
            primary_result = await primary_fetcher.fetch_with_fallback(title, category=category, top_k=1)
            if primary_result and primary_result.get("url"):
                return self._format_image_result(primary_result)

            if fallback_url:
                return {"url": fallback_url, "credit": None}

            secondary_fetcher = self._get_image_fetcher(["openverse", "wikimedia", "pixabay", "pexels"], ImageFetcher)
            secondary_result = await secondary_fetcher.fetch_with_fallback(title, category=category, top_k=1)
            if secondary_result and secondary_result.get("url"):
                return self._format_image_result(secondary_result)
        except Exception:
            logger.debug("Semantic image fetch failed for: %s", title, exc_info=True)
        return {"url": fallback_url, "credit": None} if fallback_url else None

    def _get_image_fetcher(self, sources: list[str], image_fetcher_cls):
        key = tuple(sources)
        fetcher = self._image_fetchers.get(key)
        if fetcher is None:
            fetcher = image_fetcher_cls(sources=sources)
            self._image_fetchers[key] = fetcher
        return fetcher

    def _format_image_result(self, result: dict) -> dict:
        creator = (result.get("creator") or "").strip()
        provider = (result.get("provider") or "").strip()
        lic = (result.get("license") or "").strip()
        source_url = (result.get("source_url") or "").strip()
        parts = []
        if creator:
            parts.append(creator)
        if provider:
            parts.append(provider.title())
        credit_text = " / ".join(parts) if parts else provider.title()
        if lic:
            credit_text = f"{credit_text} ({lic})" if credit_text else lic
        credit_payload = {
            "credit": credit_text,
            "source_url": source_url,
            "provider": provider,
            "license": lic,
        }
        return {"url": result["url"], "credit": credit_payload}
    
    async def get_processing_stats(self) -> Dict:
        """Get content processing statistics."""
        from sqlalchemy import func
        
        # Count by status
        result = await self.db.execute(
            select(RawContent.status, func.count(RawContent.id))
            .group_by(RawContent.status)
        )
        status_counts = dict(result.all())
        
        # Count processed content
        result = await self.db.execute(
            select(func.count(ProcessedContent.id))
        )
        processed_count = result.scalar()
        
        # Average attractiveness score
        result = await self.db.execute(
            select(func.avg(ProcessedContent.attractiveness_score))
        )
        avg_score = result.scalar() or 0
        
        return {
            "raw_content": {
                "pending": status_counts.get("pending", 0),
                "processed": status_counts.get("processed", 0),
                "failed": status_counts.get("failed", 0),
                "rejected": status_counts.get("rejected", 0),
            },
            "processed_content": processed_count,
            "average_attractiveness_score": round(avg_score, 2)
        }
