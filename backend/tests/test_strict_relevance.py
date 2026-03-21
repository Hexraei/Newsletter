"""Regression tests for strict relevance gating and feed filtering."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.config import settings
from app.models import ProcessedContent, RawContent, Source
from app.services.content_processor import ContentProcessor
from app.services.feed_service import FeedService
import app.services.feed_service as feed_service_module
from app.services.dept_relevance import assign_departments


def _make_raw(title: str, content: str, *, published_at: datetime | None = None, scraped_at: datetime | None = None) -> RawContent:
    return RawContent(
        source_id=1,
        original_url=f"https://example.com/{uuid4()}",
        original_title=title,
        original_content=content,
        content_hash=str(uuid4()).replace("-", ""),
        published_at=published_at,
        scraped_at=scraped_at,
    )


def _make_processor() -> ContentProcessor:
    # These method-level tests don't need DB/AI dependencies.
    return ContentProcessor.__new__(ContentProcessor)


def test_strict_gate_blocks_low_geo_and_low_actionability(monkeypatch: pytest.MonkeyPatch) -> None:
    processor = _make_processor()
    raw = _make_raw("General tech chatter", "Random global update without student value.")
    source = Source(name="Generic Blog", source_type="rss", url="https://example.com", platform="rss")

    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72, raising=False)

    passed, geo, actionability, knowledge = processor._passes_strict_relevance_gate(raw, source)

    assert passed is False
    assert geo < 45
    assert actionability < 25
    assert knowledge < 32


def test_strict_gate_allows_global_actionability_override(monkeypatch: pytest.MonkeyPatch) -> None:
    processor = _make_processor()
    raw = _make_raw(
        "Internship application deadline this week",
        "Apply now. Internship eligibility, registration, campus drive, hiring, job and scholarship details.",
    )
    source = Source(name="Generic Blog", source_type="rss", url="https://example.com", platform="rss")

    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72, raising=False)

    passed, geo, actionability, _knowledge = processor._passes_strict_relevance_gate(raw, source)

    assert passed is True
    assert geo < 45
    assert actionability >= 65


def test_strict_gate_allows_knowledge_signal_path(monkeypatch: pytest.MonkeyPatch) -> None:
    processor = _make_processor()
    raw = _make_raw(
        "IEEE paper on robotics control systems and benchmark datasets",
        "New research publication and conference results for autonomous robotics and control systems.",
    )
    source = Source(name="IEEE Spectrum", source_type="academic", url="https://example.com", platform="rss")

    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72, raising=False)

    passed, _geo, actionability, knowledge = processor._passes_strict_relevance_gate(raw, source)

    assert passed is True
    assert actionability < 25
    assert knowledge >= 32


def test_noise_filter_rejects_self_promo_pattern() -> None:
    processor = _make_processor()
    raw = _make_raw("I will not promote my channel", "Please subscribe and share your thoughts?")

    assert processor._is_noise_content(raw) is True


def test_resolve_publish_time_prefers_source_timestamp() -> None:
    processor = _make_processor()
    published = datetime(2026, 1, 20, 9, 30)  # naive timestamp from source
    scraped = datetime(2026, 1, 21, 10, 0, tzinfo=timezone.utc)
    raw = _make_raw("Title", "Content", published_at=published, scraped_at=scraped)

    resolved = processor._resolve_publish_time(raw)

    assert resolved.year == 2026 and resolved.month == 1 and resolved.day == 20
    assert resolved.tzinfo == timezone.utc


def test_strict_prefilter_matches_gate_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    processor = _make_processor()
    raw = _make_raw("Global roundup", "Generic update without India student actionability.")
    source = Source(name="Generic Source", source_type="rss", url="https://example.com", platform="rss")
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72, raising=False)

    gate = processor._passes_strict_relevance_gate(raw, source)
    prefilter = processor._strict_prefilter_decision(raw, source)

    assert prefilter == gate


def _make_processed(title: str, department: str, *, geo: int, actionability: int, score: int = 80) -> ProcessedContent:
    return ProcessedContent(
        title=title,
        summary="summary",
        status="published",
        content_type="news",
        department_tags=[department],
        topic_tags=["test"],
        attractiveness_score=score,
        view_count=score,
        published_at=datetime.now(timezone.utc),
        visualizations={
            "geo_relevance_score": geo,
            "student_actionability_score": actionability,
            "knowledge_relevance_score": 0,
        },
    )


@pytest.mark.asyncio
async def test_trending_strict_filter_excludes_non_relevant(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    dept = f"TEST-{uuid4().hex[:8]}"
    keep_item = _make_processed("Strict keep", dept, geo=85, actionability=50, score=95)
    drop_item = _make_processed("Strict drop", dept, geo=10, actionability=10, score=99)
    db_session.add_all([keep_item, drop_item])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72, raising=False)

    service = FeedService(db_session)
    items = await service.get_trending_content(limit=10, department=dept)
    titles = {item["title"] for item in items}

    assert "Strict keep" in titles
    assert "Strict drop" not in titles


@pytest.mark.asyncio
async def test_trending_strict_mode_disables_cross_department_supplement(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_dept = f"TEST-{uuid4().hex[:8]}"
    other_dept = f"TEST-{uuid4().hex[:8]}"
    only_primary = _make_processed("Only primary", primary_dept, geo=80, actionability=45, score=88)
    other_item = _make_processed("Other dept item", other_dept, geo=90, actionability=50, score=99)
    db_session.add_all([only_primary, other_item])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72, raising=False)

    service = FeedService(db_session)
    items = await service.get_trending_content(limit=3, department=primary_dept)

    assert len(items) == 1
    assert items[0]["title"] == "Only primary"


def test_assign_departments_does_not_map_generic_career_to_cs_cluster() -> None:
    title = "Internship applications open for engineering students"
    content = "Students can apply before the deadline. Registration and eligibility details announced."
    tags = assign_departments(title, content, source_dept_tags=[], source_type="india-career")
    assert tags == []


def test_assign_departments_does_not_treat_engineering_as_engine_keyword() -> None:
    title = "Engineering internship registrations are now open"
    content = "Engineering students can apply before the deadline. Eligibility details are published."
    tags = assign_departments(title, content, source_dept_tags=[], source_type="india-career")
    assert "ME" not in tags
    assert tags == []


def test_assign_departments_matches_whole_word_engine_for_me() -> None:
    title = "Automotive engine design role announced"
    content = "Candidates with automotive engine and machining exposure are preferred."
    tags = assign_departments(title, content, source_dept_tags=[], source_type="india-tech")
    assert "ME" in tags


def test_assign_departments_maps_ece_specific_content() -> None:
    title = "RFIC Analog Engineer hiring for semiconductor VLSI team"
    content = "Strong background in RF, chip design, VLSI, and embedded systems required."
    tags = assign_departments(title, content, source_dept_tags=[], source_type="india-tech")
    assert "ECE" in tags


@pytest.mark.asyncio
async def test_get_career_content_respects_department_filter(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    ece_item = _make_processed("ECE role", "ECE", geo=85, actionability=60, score=92)
    ece_item.category = "career"
    me_item = _make_processed("ME role", "ME", geo=85, actionability=60, score=95)
    me_item.category = "career"
    db_session.add_all([ece_item, me_item])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)

    service = FeedService(db_session)
    ece_items = await service.get_career_content(limit=10, department="ECE")
    titles = {item["title"] for item in ece_items}

    assert "ECE role" in titles
    assert "ME role" not in titles
