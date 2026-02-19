"""Unit tests for lightweight ranking engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.ranking_engine import (
    BreakingNewsScorer,
    EngagementScorer,
    LowQualityFilter,
    NewsCandidate,
    RecencyScorer,
    SourceDiversityScorer,
    WeightedCombiner,
    rank_breaking,
    rank_department,
    rank_student_stories,
    rank_trending,
)


FIXED_NOW = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)


def make_item(
    title: str,
    source: str,
    *,
    hours_ago: float = 1.0,
    upvotes: int = 0,
    comments: int = 0,
    stars: int = 0,
    forks: int = 0,
    content: str = "",
    content_hash: str | None = None,
) -> dict:
    published = (FIXED_NOW - timedelta(hours=hours_ago)).isoformat()
    return {
        "title": title,
        "source": source,
        "url": f"https://example.com/{title.replace(' ', '-').lower()}",
        "content": content,
        "published_at": published,
        "engagement": {
            "upvotes": upvotes,
            "comments": comments,
            "stars": stars,
            "forks": forks,
        },
        "content_hash": content_hash or f"hash-{title}",
    }


def test_engagement_scorer_increases_with_engagement() -> None:
    low = NewsCandidate(item=make_item("Low", "Hacker News", upvotes=5, comments=1))
    high = NewsCandidate(item=make_item("High", "Hacker News", upvotes=180, comments=55))

    candidates = [low, high]
    EngagementScorer.score(candidates)

    assert high.engagement_score > low.engagement_score


def test_recency_scorer_decays_older_items() -> None:
    fresh = NewsCandidate(item=make_item("Fresh", "Hacker News", hours_ago=1))
    stale = NewsCandidate(item=make_item("Stale", "Hacker News", hours_ago=20))

    RecencyScorer.score([fresh, stale], decay_lambda=0.3, now=FIXED_NOW)

    assert fresh.recency_score > stale.recency_score


def test_breaking_news_scorer_boosts_urgency_keywords() -> None:
    urgent = NewsCandidate(
        item=make_item(
            "Critical security outage hits campus systems",
            "Reddit",
            hours_ago=0.5,
            upvotes=40,
            comments=15,
            content="breaking incident and urgent response",
        )
    )
    normal = NewsCandidate(
        item=make_item(
            "New programming language tutorial",
            "Reddit",
            hours_ago=0.5,
            upvotes=40,
            comments=15,
            content="general update",
        )
    )

    candidates = [urgent, normal]
    BreakingNewsScorer.score(candidates, now=FIXED_NOW)

    assert urgent.urgency_score > normal.urgency_score


def test_source_diversity_penalizes_repeated_sources() -> None:
    first = NewsCandidate(item=make_item("A", "Hacker News"), final_score=1.0)
    second = NewsCandidate(item=make_item("B", "Hacker News"), final_score=1.0)
    third = NewsCandidate(item=make_item("C", "GitHub"), final_score=1.0)

    ordered = [first, second, third]
    SourceDiversityScorer.apply(ordered)

    assert second.diversity_penalty < first.diversity_penalty
    assert second.final_score < first.final_score
    assert third.diversity_penalty == 1.0


def test_weighted_combiner_uses_section_weights() -> None:
    candidate = NewsCandidate(
        item=make_item("Weighted", "Hacker News"),
        engagement_score=1.0,
        recency_score=0.5,
        urgency_score=0.25,
        relevance_score=0.4,
    )

    WeightedCombiner.combine([candidate], section="trending")
    expected = (0.50 * 1.0) + (0.25 * 0.5) + (0.10 * 0.25) + (0.15 * 0.4)

    assert abs(candidate.final_score - expected) < 1e-9


def test_rank_breaking_orders_urgent_recent_items_first() -> None:
    urgent = make_item(
        "Breaking outage impacts student portal",
        "Reddit",
        hours_ago=0.8,
        upvotes=120,
        comments=80,
        content="urgent incident security outage",
    )
    regular = make_item(
        "Open source release notes",
        "GitHub",
        hours_ago=0.8,
        upvotes=180,
        comments=20,
        content="release update",
    )

    ranked = rank_breaking([regular, urgent], limit=2, now=FIXED_NOW)

    assert ranked[0].item["title"] == urgent["title"]


def test_rank_department_and_student_story_relevance() -> None:
    dept_item = make_item(
        "Distributed systems and operating systems update",
        "Hacker News",
        hours_ago=4,
        upvotes=70,
        comments=20,
        content="computer science curriculum and algorithm study",
    )
    story_item = make_item(
        "Student internship project wins hackathon",
        "Reddit",
        hours_ago=6,
        upvotes=60,
        comments=35,
        content="career community mentorship",
    )

    department_ranked = rank_department([dept_item, story_item], limit=2, now=FIXED_NOW)
    stories_ranked = rank_student_stories([dept_item, story_item], limit=2, now=FIXED_NOW)

    assert department_ranked[0].item["title"] == dept_item["title"]
    assert stories_ranked[0].item["title"] == story_item["title"]


def test_rank_trending_prefers_higher_engagement() -> None:
    high = make_item("High engagement trend", "GitHub", upvotes=400, comments=120, hours_ago=8)
    low = make_item("Low engagement trend", "GitHub", upvotes=20, comments=2, hours_ago=8)

    ranked = rank_trending([low, high], limit=2, now=FIXED_NOW)

    assert ranked[0].item["title"] == high["title"]


def test_filters_remove_duplicates_stale_and_low_quality() -> None:
    duplicate_a = make_item(
        "Duplicate A",
        "Hacker News",
        upvotes=10,
        comments=1,
        content_hash="dup-1",
        hours_ago=2,
        content="some content",
    )
    duplicate_b = make_item(
        "Duplicate B",
        "GitHub",
        upvotes=90,
        comments=10,
        content_hash="dup-1",
        hours_ago=2,
        content="some different content",
    )
    stale = make_item(
        "Very old outage",
        "Reddit",
        upvotes=200,
        comments=130,
        hours_ago=80,
        content="breaking outage",
    )
    low_quality = make_item(
        "Low quality",
        "Medium",
        upvotes=0,
        comments=0,
        content="",
        hours_ago=1,
    )

    # LowQualityFilter validates the low quality condition directly.
    assert len(LowQualityFilter.apply([low_quality])) == 0

    ranked = rank_breaking([duplicate_a, duplicate_b, stale], limit=5, now=FIXED_NOW)
    titles = [candidate.item["title"] for candidate in ranked]

    assert "Very old outage" not in titles
    assert len(titles) == 1
