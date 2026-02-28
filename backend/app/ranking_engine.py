"""Lightweight multi-signal ranking pipeline for newsletter feeds."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass
class NewsCandidate:
    item: dict
    engagement_score: float = 0.0
    recency_score: float = 0.0
    urgency_score: float = 0.0
    relevance_score: float = 0.0
    diversity_penalty: float = 1.0
    final_score: float = 0.0
    section: str = ""


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _parse_json_field(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        raw = value.strip().replace("Z", "+00:00")
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw)
        except Exception:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_hours(item: dict, now: datetime | None = None) -> float | None:
    published = _parse_datetime(item.get("published_at"))
    if published is None:
        return None
    current = now or datetime.now(timezone.utc)
    return max(0.0, (current - published).total_seconds() / 3600.0)


def _text_blob(item: dict) -> str:
    metadata = _parse_json_field(item.get("metadata"))
    return " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("content") or ""),
            str(item.get("summary") or ""),
            str(item.get("source") or ""),
            str(item.get("category") or ""),
            str(metadata.get("category") or ""),
        ]
    ).lower()


def _extract_engagement(item: dict) -> dict[str, int]:
    engagement = _parse_json_field(item.get("engagement"))
    content = str(item.get("content") or "")
    score_match = re.search(r"score\s*:\s*(\d+)", content, flags=re.IGNORECASE)
    comments_match = re.search(r"comments\s*:\s*(\d+)", content, flags=re.IGNORECASE)

    upvotes = _safe_int(engagement.get("upvotes"))
    comments = _safe_int(engagement.get("comments"))
    stars = _safe_int(engagement.get("stars"))
    forks = _safe_int(engagement.get("forks"))

    if upvotes == 0 and score_match:
        upvotes = _safe_int(score_match.group(1))
    if comments == 0 and comments_match:
        comments = _safe_int(comments_match.group(1))

    return {
        "upvotes": max(0, upvotes),
        "comments": max(0, comments),
        "stars": max(0, stars),
        "forks": max(0, forks),
    }


def _raw_engagement(item: dict) -> float:
    metrics = _extract_engagement(item)
    return (
        metrics["upvotes"]
        + 2.0 * metrics["comments"]
        + 1.2 * metrics["stars"]
        + 1.4 * metrics["forks"]
    )


def _short_summary(item: dict, max_len: int = 140) -> str:
    content = str(item.get("content") or "").strip()
    if content.lower().startswith("score:"):
        content = ""
    source = str(item.get("source") or "Campus Tech")
    text = content if content else f"{source} update for CS students."
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 3] + "..."


class DuplicateFilter:
    @staticmethod
    def apply(items: Iterable[dict]) -> list[dict]:
        seen: set[str] = set()
        output: list[dict] = []
        for item in items:
            content_hash = str(item.get("content_hash") or "").strip().lower()
            fallback = f"{str(item.get('title') or '').strip().lower()}|{str(item.get('url') or '').strip().lower()}"
            key = content_hash or fallback
            if not key or key in seen:
                continue
            seen.add(key)
            output.append(item)
        return output


class AgeFilter:
    @staticmethod
    def apply(items: Iterable[dict], max_age_hours: float, now: datetime | None = None) -> list[dict]:
        if max_age_hours <= 0:
            return list(items)
        output: list[dict] = []
        for item in items:
            age = _age_hours(item, now=now)
            if age is None or age <= max_age_hours:
                output.append(item)
        return output


class LowQualityFilter:
    @staticmethod
    def apply(items: Iterable[dict]) -> list[dict]:
        output: list[dict] = []
        for item in items:
            title = str(item.get("title") or "").strip()
            content = str(item.get("content") or "").strip()
            if not title:
                continue
            if _raw_engagement(item) <= 0 and not content:
                continue
            output.append(item)
        return output


class EngagementScorer:
    @staticmethod
    def score(candidates: list[NewsCandidate]) -> None:
        if not candidates:
            return

        raw_by_source: dict[str, list[float]] = defaultdict(list)
        raw_values: list[float] = []
        for candidate in candidates:
            source = str(candidate.item.get("source") or "unknown").lower()
            metrics = _extract_engagement(candidate.item)
            raw = (
                1.0 * math.log1p(metrics["upvotes"])
                + 1.25 * math.log1p(metrics["comments"])
                + 0.9 * math.log1p(metrics["stars"])
                + 1.1 * math.log1p(metrics["forks"])
            )
            raw_by_source[source].append(raw)
            raw_values.append(raw)

        global_max = max(raw_values) if raw_values else 1.0
        source_max = {source: max(values) for source, values in raw_by_source.items() if values}

        for candidate in candidates:
            source = str(candidate.item.get("source") or "unknown").lower()
            metrics = _extract_engagement(candidate.item)
            raw = (
                1.0 * math.log1p(metrics["upvotes"])
                + 1.25 * math.log1p(metrics["comments"])
                + 0.9 * math.log1p(metrics["stars"])
                + 1.1 * math.log1p(metrics["forks"])
            )
            local = raw / max(source_max.get(source, 1.0), 1e-6)
            global_norm = raw / max(global_max, 1e-6)
            candidate.engagement_score = max(0.0, min(1.0, 0.65 * local + 0.35 * global_norm))


class RecencyScorer:
    @staticmethod
    def score(candidates: list[NewsCandidate], decay_lambda: float, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        safe_lambda = max(0.0, decay_lambda)
        for candidate in candidates:
            age = _age_hours(candidate.item, now=current)
            candidate.recency_score = 0.2 if age is None else math.exp(-safe_lambda * age)


class BreakingNewsScorer:
    # Only specific, high-signal event terms — not generic words like "launch" or "security"
    KEYWORDS = (
        "breaking",
        "urgent",
        "critical",
        "breach",
        "outage",
        "down",
        "incident",
        "attack",
        "zero-day",
        "vulnerability",
        "exploit",
        "hacked",
        "leak",
        "ban",
        "lawsuit",
        "shutdown",
        "acquires",
        "emergency",
        "bankrupt",
        "offline",
        "indicted",
        "fired ceo",
        "data breach",
    )

    @classmethod
    def score(cls, candidates: list[NewsCandidate], now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        for candidate in candidates:
            text = _text_blob(candidate.item)
            keyword_hits = sum(1 for keyword in cls.KEYWORDS if keyword in text)
            raw = _raw_engagement(candidate.item)
            age = _age_hours(candidate.item, now=current) or 12.0
            velocity = math.log1p(raw) / max(1.0, age)
            # Velocity (engagement/age) is more objective — weight it more than keyword hits
            keyword_score = min(1.0, 0.2 * keyword_hits)
            velocity_score = min(1.0, velocity / 2.5)
            candidate.urgency_score = max(0.0, min(1.0, keyword_score + velocity_score))


class CategoryRelevanceScorer:
    SECTION_KEYWORDS = {
        "breaking": (
            "breaking",
            "urgent",
            "critical",
            "outage",
            "incident",
            "breach",
            "data breach",
            "zero-day",
            "vulnerability",
            "exploit",
            "hacked",
            "ban",
            "lawsuit",
            "shutdown",
            "acquires",
            "acquisition",
            "merger",
            "emergency",
            "offline",
            "attack",
            "recall",
            "indicted",
            "bankrupt",
        ),
        ),
        "department": (
            "computer science",
            "algorithm",
            "data structure",
            "operating system",
            "distributed systems",
            "database",
            "compiler",
            "open source",
            "software engineering",
            "programming",
            "github",
            "cybersecurity",
            "machine learning",
            "neural network",
            "deep learning",
            "devops",
            "kubernetes",
            "docker",
            "linux",
            "rust",
            "golang",
            "typescript",
            "webassembly",
            "api",
            "framework",
            "library",
            "self-hosted",
            "selfhosted",
            "llama",
            "localllama",
            "netsec",
        ),
        "student_stories": (
            "student",
            "internship",
            "intern",
            "career",
            "community",
            "hackathon",
            "project",
            "resume",
            "interview",
            "campus",
            "mentorship",
            "portfolio",
            "leetcode",
            "job",
            "hiring",
            "salary",
            "offer",
            "faang",
            "new grad",
            "freshman",
            "sophomore",
            "junior",
            "senior",
            "undergrad",
            "graduate",
            "cs major",
            "bootcamp",
            "self-taught",
            "side project",
            "co-op",
            "fellowship",
            "scholarship",
            "advice",
            "experience",
            "learn programming",
            "learning",
            "first job",
            "remote work",
            "work-life",
            "layoff",
            "laid off",
        ),
        "trending": (
            "industry",
            "market",
            "regulation",
            "policy",
            "economy",
            "startup",
            "funding",
            "venture capital",
            "ipo",
            "acquisition",
            "merger",
            "valuation",
            "billion",
            "trillion",
            "wall street",
            "stock",
            "investor",
            "singularity",
            "futurology",
            "future",
            "biotech",
            "climate",
            "energy",
            "healthcare",
            "pharmaceutical",
            "autonomous",
            "robotics",
            "quantum",
            "geopolitics",
            "trade war",
            "tariff",
            "antitrust",
            "monopoly",
            "gdpr",
            "privacy law",
            "consumer",
            "supply chain",
            "semiconductor",
            "chip",
            "manufacture",
            "factory",
            "election",
            "government",
            "defense",
            "space",
            "nuclear",
            "hydrogen",
            "renewable",
            "emission",
        ),
    }

    # ── Subreddit-level source hints ──
    # These boost relevance based on which subreddit the item came from,
    # giving each section a clear signal even when title keywords are ambiguous.
    SOURCE_HINTS = {
        # Breaking: credible established news outlets get a strong boost
        "breaking": {
            "techcrunch": 0.22,
            "the verge": 0.22,
            "wired": 0.20,
            "ars technica": 0.22,
            "reuters": 0.26,
            "bloomberg": 0.26,
            "associated press": 0.24,
            "bbc": 0.22,
            "financial times": 0.22,
            "wsj": 0.22,
            "wall street journal": 0.22,
            "mit technology review": 0.20,
            "the guardian": 0.18,
            "hacker news": 0.12,
            "r/technology": 0.08,
            "r/worldnews": 0.10,
            "r/technews": 0.10,
        },
        "department": {
            "hacker news": 0.14,
            "github": 0.16,
            "medium": 0.08,
            "r/programming": 0.14,
            "r/compsci": 0.16,
            "r/netsec": 0.14,
            "r/machinelearning": 0.12,
            "r/localllama": 0.12,
            "r/artificial": 0.10,
            "r/python": 0.10,
            "r/javascript": 0.10,
            "r/webdev": 0.10,
            "r/selfhosted": 0.10,
        },
        "student_stories": {
            "r/cscareerquestions": 0.22,
            "r/csmajors": 0.24,
            "r/experienceddevs": 0.16,
            "r/learnprogramming": 0.18,
            "r/cs50": 0.18,
            "reddit": 0.06,
            "medium": 0.06,
            "product hunt": 0.04,
        },
        "trending": {
            "r/singularity": 0.24,
            "r/futurology": 0.22,
            "r/startups": 0.16,
            "r/technews": 0.16,
            "r/artificialinteligence": 0.14,
            "r/stocks": 0.18,
            "r/energy": 0.16,
            "r/biotech": 0.18,
            "r/climatetech": 0.16,
            "r/economics": 0.14,
            "r/entrepreneur": 0.12,
            "r/technology": 0.06,
            "product hunt": 0.08,
        },
    }

    @classmethod
    def score(cls, candidates: list[NewsCandidate], section: str) -> None:
        keywords = cls.SECTION_KEYWORDS.get(section, ())
        source_hints = cls.SOURCE_HINTS.get(section, {})
        for candidate in candidates:
            text = _text_blob(candidate.item)
            hits = sum(1 for keyword in keywords if keyword in text)
            keyword_score = min(1.0, hits / 4.0) if keywords else 0.0

            # Build a combined source string that includes both the source
            # field ("Reddit - r/singularity") and metadata.subreddit for
            # more reliable subreddit-level matching.
            source = str(candidate.item.get("source") or "").lower()
            metadata = _parse_json_field(candidate.item.get("metadata"))
            subreddit = str(metadata.get("subreddit") or "").lower()
            source_blob = f"{source} r/{subreddit}" if subreddit else source

            source_boost = 0.0
            for token, boost in source_hints.items():
                if token in source_blob:
                    source_boost = max(source_boost, boost)
            candidate.relevance_score = max(0.0, min(1.0, keyword_score + source_boost))


class SourceDiversityScorer:
    @staticmethod
    def apply(candidates: list[NewsCandidate], floor: float = 0.55, decay: float = 0.72) -> None:
        seen_by_source: dict[str, int] = defaultdict(int)
        safe_floor = max(0.0, min(0.95, floor))
        safe_decay = max(0.1, min(0.99, decay))
        for candidate in candidates:
            source = str(candidate.item.get("source") or "unknown").lower()
            position = seen_by_source[source]
            multiplier = ((1.0 - safe_floor) * (safe_decay**position)) + safe_floor
            candidate.diversity_penalty = multiplier
            candidate.final_score *= multiplier
            seen_by_source[source] += 1


class WeightedCombiner:
    SECTION_WEIGHTS: dict[str, dict[str, float]] = {
        # Breaking: engagement velocity + recency dominate (objective signals); less weight on keywords
        "breaking": {"engagement": 0.35, "recency": 0.25, "urgency": 0.25, "relevance": 0.15},
        "department": {"engagement": 0.25, "recency": 0.15, "urgency": 0.05, "relevance": 0.55},
        "student_stories": {"engagement": 0.25, "recency": 0.15, "urgency": 0.05, "relevance": 0.55},
        "trending": {"engagement": 0.30, "recency": 0.20, "urgency": 0.05, "relevance": 0.45},
    }

    @classmethod
    def combine(cls, candidates: list[NewsCandidate], section: str) -> None:
        weights = cls.SECTION_WEIGHTS.get(section, cls.SECTION_WEIGHTS["trending"])
        for candidate in candidates:
            candidate.final_score = (
                weights["engagement"] * candidate.engagement_score
                + weights["recency"] * candidate.recency_score
                + weights["urgency"] * candidate.urgency_score
                + weights["relevance"] * candidate.relevance_score
            )


def _rank_section(
    items: Iterable[dict],
    section: str,
    limit: int,
    max_age_hours: float,
    recency_lambda: float,
    min_relevance: float,
    now: datetime | None = None,
) -> list[NewsCandidate]:
    filtered = DuplicateFilter.apply(items)
    filtered = AgeFilter.apply(filtered, max_age_hours=max_age_hours, now=now)
    filtered = LowQualityFilter.apply(filtered)

    candidates = [NewsCandidate(item=item) for item in filtered]
    if not candidates:
        return []

    EngagementScorer.score(candidates)
    RecencyScorer.score(candidates, decay_lambda=recency_lambda, now=now)
    BreakingNewsScorer.score(candidates, now=now)
    CategoryRelevanceScorer.score(candidates, section=section)

    picked = candidates
    if min_relevance > 0:
        strong = [candidate for candidate in candidates if candidate.relevance_score >= min_relevance]
        if len(strong) >= min(3, limit):
            picked = strong

    WeightedCombiner.combine(picked, section=section)
    picked.sort(key=lambda candidate: candidate.final_score, reverse=True)
    SourceDiversityScorer.apply(picked)
    picked.sort(key=lambda candidate: candidate.final_score, reverse=True)

    clamped_limit = max(1, min(80, limit))
    result = picked[:clamped_limit]
    for candidate in result:
        candidate.section = section
    return result


def rank_breaking(items: Iterable[dict], limit: int = 8, now: datetime | None = None) -> list[NewsCandidate]:
    return _rank_section(items, "breaking", limit, max_age_hours=48, recency_lambda=0.30, min_relevance=0.05, now=now)


def rank_department(items: Iterable[dict], limit: int = 3, now: datetime | None = None) -> list[NewsCandidate]:
    return _rank_section(
        items,
        "department",
        limit,
        max_age_hours=24 * 7,
        recency_lambda=0.12,
        min_relevance=0.15,
        now=now,
    )


def rank_student_stories(items: Iterable[dict], limit: int = 3, now: datetime | None = None) -> list[NewsCandidate]:
    return _rank_section(
        items,
        "student_stories",
        limit,
        max_age_hours=24 * 7,
        recency_lambda=0.15,
        min_relevance=0.12,
        now=now,
    )


def rank_trending(items: Iterable[dict], limit: int = 20, now: datetime | None = None) -> list[NewsCandidate]:
    return _rank_section(items, "trending", limit, max_age_hours=24 * 7, recency_lambda=0.05, min_relevance=0.10, now=now)


def rank_all_sections(
    items: Iterable[dict],
    limits: dict[str, int] | None = None,
    now: datetime | None = None,
) -> dict[str, list[NewsCandidate]]:
    items_list = list(items)
    limits = limits or {}
    return {
        "breaking": rank_breaking(items_list, limit=_safe_int(limits.get("breaking")) or 8, now=now),
        "department": rank_department(items_list, limit=_safe_int(limits.get("department")) or 3, now=now),
        "student_stories": rank_student_stories(
            items_list,
            limit=_safe_int(limits.get("student_stories")) or 3,
            now=now,
        ),
        "trending": rank_trending(items_list, limit=_safe_int(limits.get("trending")) or 3, now=now),
    }


def candidate_to_feed_item(candidate: NewsCandidate) -> dict:
    item = candidate.item
    metadata = _parse_json_field(item.get("metadata"))
    category = str(metadata.get("category") or item.get("category") or "general")
    return {
        "title": str(item.get("title") or ""),
        "summary": _short_summary(item),
        "source": str(item.get("source") or "Campus Tech"),
        "url": str(item.get("url") or "#"),
        "original_url": str(item.get("url") or "#"),
        "category": category,
        "is_breaking": candidate.section == "breaking",
        "published_at": item.get("published_at"),
        "attractiveness_score": round(candidate.engagement_score * 100, 4),
        "engagement_score": round(candidate.engagement_score, 6),
        "recency_score": round(candidate.recency_score, 6),
        "urgency_score": round(candidate.urgency_score, 6),
        "relevance_score": round(candidate.relevance_score, 6),
        "diversity_penalty": round(candidate.diversity_penalty, 6),
        "final_score": round(candidate.final_score, 6),
        "section": candidate.section,
    }


def rank_all_sections_as_feed(
    items: Iterable[dict],
    limits: dict[str, int] | None = None,
    now: datetime | None = None,
) -> dict[str, list[dict]]:
    ranked = rank_all_sections(items, limits=limits, now=now)
    return {
        "breaking": [candidate_to_feed_item(candidate) for candidate in ranked["breaking"]],
        "department": [candidate_to_feed_item(candidate) for candidate in ranked["department"]],
        "student_stories": [candidate_to_feed_item(candidate) for candidate in ranked["student_stories"]],
        "trending": [candidate_to_feed_item(candidate) for candidate in ranked["trending"]],
    }
