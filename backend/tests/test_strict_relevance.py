"""Regression tests for strict relevance gating and feed filtering."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.config import settings
from app.models import ProcessedContent, RawContent, Source
from app.services.cache_service import get_cache
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

    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 30, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 15, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 58, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 65, raising=False)

    passed, geo, actionability, knowledge = processor._passes_strict_relevance_gate(raw, source)

    assert passed is False
    assert geo < 30
    assert actionability < 15
    assert knowledge < 20


def test_strict_gate_allows_global_actionability_override(monkeypatch: pytest.MonkeyPatch) -> None:
    processor = _make_processor()
    raw = _make_raw(
        "Internship application deadline this week",
        "Apply now. Internship eligibility, registration, campus drive, hiring, job and scholarship details.",
    )
    source = Source(name="Generic Blog", source_type="rss", url="https://example.com", platform="rss")

    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 30, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 15, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 58, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 65, raising=False)

    passed, geo, actionability, _knowledge = processor._passes_strict_relevance_gate(raw, source)

    assert passed is True
    assert geo < 30
    assert actionability >= 58


def test_strict_gate_allows_knowledge_signal_path(monkeypatch: pytest.MonkeyPatch) -> None:
    processor = _make_processor()
    raw = _make_raw(
        "IEEE paper on robotics control systems and benchmark datasets",
        "New research publication and conference results for autonomous robotics and control systems.",
    )
    source = Source(name="IEEE Spectrum", source_type="academic", url="https://example.com", platform="rss")

    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 30, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 15, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 58, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 65, raising=False)

    passed, _geo, actionability, knowledge = processor._passes_strict_relevance_gate(raw, source)

    assert passed is True
    assert actionability < 15
    assert knowledge >= 20


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
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 30, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 15, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 58, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 65, raising=False)

    gate = processor._passes_strict_relevance_gate(raw, source)
    prefilter = processor._strict_prefilter_decision(raw, source)

    assert prefilter == gate


def _make_processed(
    title: str,
    department: str,
    *,
    geo: int,
    actionability: int,
    knowledge: int = 0,
    score: int = 80,
) -> ProcessedContent:
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
            "knowledge_relevance_score": knowledge,
        },
    )


def _make_source(name: str, source_type: str, url: str) -> Source:
    return Source(name=name, source_type=source_type, url=url, platform="rss")


def _make_raw_for_source(source_id: int, url: str, title: str) -> RawContent:
    return RawContent(
        source_id=source_id,
        original_url=url,
        original_title=title,
        original_content="raw body",
        content_hash=uuid4().hex,
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
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 30, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 15, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 58, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 65, raising=False)

    service = FeedService(db_session)
    items = await service.get_trending_content(limit=10, department=dept)
    titles = {item["title"] for item in items}

    assert "Strict keep" in titles
    assert "Strict drop" not in titles


@pytest.mark.asyncio
async def test_trending_strict_mode_dedupes_near_repeat_titles_with_ranking_preference(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dept = f"TEST-{uuid4().hex[:8]}"
    keep_item = _make_processed("Mega Internship Drive 2026", dept, geo=88, actionability=55, score=79)
    drop_repeat = _make_processed("mega internship-drive 2026!!!", dept, geo=92, actionability=60, score=70)
    other_item = _make_processed("Distinct scholarship update", dept, geo=90, actionability=55, score=68)
    db_session.add_all([keep_item, drop_repeat, other_item])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 30, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 15, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 58, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_SOURCE_DIVERSITY_CAP", 2, raising=False)

    service = FeedService(db_session)
    items = await service.get_trending_content(limit=5, department=dept)
    titles = [item["title"] for item in items]

    assert "Mega Internship Drive 2026" in titles
    assert "mega internship-drive 2026!!!" not in titles
    assert "Distinct scholarship update" in titles


@pytest.mark.asyncio
async def test_trending_strict_mode_supplements_sparse_department_with_relevant_items(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_dept = f"TEST-{uuid4().hex[:8]}"
    other_dept = f"TEST-{uuid4().hex[:8]}"
    only_primary = _make_processed("Only primary", primary_dept, geo=80, actionability=45, score=88)
    other_item = _make_processed("Other dept item", other_dept, geo=90, actionability=50, score=96)
    non_relevant_other = _make_processed("Other non relevant", other_dept, geo=5, actionability=5, score=99)
    db_session.add_all([only_primary, other_item, non_relevant_other])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MAX_ITEMS", 1, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MIN_ATTRACTIVENESS", 80, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 30, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 15, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 58, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 65, raising=False)

    service = FeedService(db_session)
    items = await service.get_trending_content(limit=3, department=primary_dept)
    titles = {item["title"] for item in items}

    assert len(items) == 2
    assert "Only primary" in titles
    assert "Other dept item" in titles
    assert "Other non relevant" not in titles


@pytest.mark.asyncio
async def test_trending_strict_mode_supplement_applies_source_diversity_cap_when_feasible(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_dept = f"TEST-{uuid4().hex[:8]}"
    other_dept = f"TEST-{uuid4().hex[:8]}"

    source_a = _make_source("Source A", "rss", "https://a.example.com/feed")
    source_b = _make_source("Source B", "rss", "https://b.example.com/feed")
    source_c = _make_source("Source C", "reddit", "https://reddit.com/r/test")
    db_session.add_all([source_a, source_b, source_c])
    await db_session.flush()

    raw_a_1 = _make_raw_for_source(source_a.id, "https://a.example.com/story-1", "A1")
    raw_a_2 = _make_raw_for_source(source_a.id, "https://a.example.com/story-2", "A2")
    raw_b_1 = _make_raw_for_source(source_b.id, "https://b.example.com/story-1", "B1")
    raw_c_1 = _make_raw_for_source(source_c.id, "https://c.example.com/story-1", "C1")
    db_session.add_all([raw_a_1, raw_a_2, raw_b_1, raw_c_1])
    await db_session.flush()

    primary_item = _make_processed("Primary dept anchor", primary_dept, geo=25, actionability=40, knowledge=5, score=60)
    supp_a_1 = _make_processed("A supplement 1", other_dept, geo=25, actionability=40, knowledge=5, score=79)
    supp_a_1.raw_content_id = raw_a_1.id
    supp_a_2 = _make_processed("A supplement 2", other_dept, geo=25, actionability=40, knowledge=5, score=78)
    supp_a_2.raw_content_id = raw_a_2.id
    supp_b_1 = _make_processed("B supplement", other_dept, geo=25, actionability=40, knowledge=5, score=77)
    supp_b_1.raw_content_id = raw_b_1.id
    supp_c_1 = _make_processed("C supplement", other_dept, geo=25, actionability=40, knowledge=5, score=76)
    supp_c_1.raw_content_id = raw_c_1.id
    db_session.add_all([primary_item, supp_a_1, supp_a_2, supp_b_1, supp_c_1])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MAX_ITEMS", 3, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MIN_ATTRACTIVENESS", 70, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_SOURCE_DIVERSITY_CAP", 1, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 99, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 5, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 999, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 999, raising=False)

    service = FeedService(db_session)
    items = await service.get_trending_content(limit=4, department=primary_dept)
    titles = {item["title"] for item in items}

    assert len(items) == 4
    assert "Primary dept anchor" in titles
    assert "A supplement 1" in titles
    assert "A supplement 2" not in titles
    assert "B supplement" in titles
    assert "C supplement" in titles


@pytest.mark.asyncio
async def test_trending_strict_mode_can_disable_supplement_with_config(
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
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 30, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 15, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 20, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 58, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 65, raising=False)

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
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_ENABLED", False, raising=False)

    service = FeedService(db_session)
    ece_items = await service.get_career_content(limit=10, department="ECE")
    titles = {item["title"] for item in ece_items}

    assert "ECE role" in titles
    assert "ME role" not in titles


@pytest.mark.asyncio
async def test_get_career_content_strict_supplement_applies_floor_and_cap(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_dept = f"TEST-{uuid4().hex[:8]}"
    other_dept = f"TEST-{uuid4().hex[:8]}"
    primary_item = _make_processed("Primary ECE role", primary_dept, geo=85, actionability=60, score=92)
    primary_item.category = "career"
    supplement_good = _make_processed("Other high quality role", other_dept, geo=90, actionability=70, score=980)
    supplement_good.category = "career"
    supplement_low = _make_processed("Other low quality role", other_dept, geo=90, actionability=70, score=40)
    supplement_low.category = "career"
    db_session.add_all([primary_item, supplement_good, supplement_low])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MAX_ITEMS", 1, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MIN_ATTRACTIVENESS", 900, raising=False)

    service = FeedService(db_session)
    items = await service.get_career_content(limit=3, department=primary_dept)
    titles = {item["title"] for item in items}

    assert len(items) == 2
    assert "Primary ECE role" in titles
    assert "Other high quality role" in titles
    assert "Other low quality role" not in titles


@pytest.mark.asyncio
async def test_personalized_feed_strict_supplement_respects_recency(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_dept = f"TEST-{uuid4().hex[:8]}"
    other_dept = f"TEST-{uuid4().hex[:8]}"

    primary_item = _make_processed("Primary feed item", primary_dept, geo=80, actionability=55, score=86)
    supplement_fresh = _make_processed("Fresh supplement", other_dept, geo=88, actionability=60, score=980)
    supplement_stale = _make_processed("Stale supplement", other_dept, geo=90, actionability=65, score=970)
    supplement_stale.published_at = datetime.now(timezone.utc) - timedelta(days=45)
    db_session.add_all([primary_item, supplement_fresh, supplement_stale])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MAX_ITEMS", 2, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MIN_ATTRACTIVENESS", 900, raising=False)

    service = FeedService(db_session)
    response = await service.get_personalized_feed(department=primary_dept, limit=3)
    titles = {item["title"] for item in response["items"]}

    assert "Primary feed item" in titles
    assert "Fresh supplement" in titles
    assert "Stale supplement" not in titles


@pytest.mark.asyncio
async def test_breaking_news_strict_supplement_fills_missing_slots(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_dept = f"TEST-{uuid4().hex[:8]}"
    other_dept = f"TEST-{uuid4().hex[:8]}"

    primary_item = _make_processed("Primary breaking baseline", primary_dept, geo=86, actionability=52, score=45)
    supplement_item = _make_processed("Cross dept supplement breaking", other_dept, geo=92, actionability=70, score=980)
    non_relevant_high = _make_processed("Cross dept non relevant", other_dept, geo=5, actionability=5, score=999)
    db_session.add_all([primary_item, supplement_item, non_relevant_high])
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MAX_ITEMS", 1, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_SUPPLEMENT_MIN_ATTRACTIVENESS", 900, raising=False)

    service = FeedService(db_session)
    items = await service.get_breaking_news(limit=3, department=primary_dept)
    titles = {item["title"] for item in items}

    assert len(items) == 2
    assert "Primary breaking baseline" in titles
    assert "Cross dept supplement breaking" in titles
    assert "Cross dept non relevant" not in titles


@pytest.mark.asyncio
async def test_trending_falls_back_when_no_strict_relevance_data_exists(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dept = f"TEST-{uuid4().hex[:8]}"
    legacy_item = _make_processed("Legacy production item", dept, geo=0, actionability=0, knowledge=0, score=91)
    db_session.add(legacy_item)
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72, raising=False)

    service = FeedService(db_session)
    items = await service.get_trending_content(limit=5, department=dept)
    titles = {item["title"] for item in items}

    assert await service._use_strict_relevance() is False
    assert "Legacy production item" in titles


@pytest.mark.asyncio
async def test_all_sections_ignores_stale_empty_cached_feed(
    async_client,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dept = f"TEST-{uuid4().hex[:8]}"
    fallback_item = _make_processed("Cached fallback item", dept, geo=0, actionability=0, knowledge=0, score=93)
    db_session.add(fallback_item)
    await db_session.commit()

    monkeypatch.setattr(feed_service_module, "_IS_SQLITE", db_session.bind.dialect.name == "sqlite")
    monkeypatch.setattr(settings, "RELEVANCE_STRICT_MODE", True, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_GEO_SCORE", 45, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_ACTIONABILITY_SCORE", 25, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_MIN_KNOWLEDGE_SCORE", 32, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_ACTIONABILITY_OVERRIDE", 65, raising=False)
    monkeypatch.setattr(settings, "RELEVANCE_GLOBAL_KNOWLEDGE_OVERRIDE", 72, raising=False)

    empty_payload = (
        '{"breaking":[],"department":[],"trending":[],"career":[],'
        '"research_papers":{"featured":[],"papers":[]}}'
    )
    if db_session.bind.dialect.name == "sqlite":
        await db_session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS cached_feeds (
                    department TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        await db_session.execute(
            text(
                """
                INSERT INTO cached_feeds (department, data, updated_at)
                VALUES (:department, :data, CURRENT_TIMESTAMP)
                ON CONFLICT(department) DO UPDATE
                SET data = excluded.data, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"department": dept, "data": empty_payload},
        )
    else:
        await db_session.execute(
            text(
                """
                INSERT INTO cached_feeds (department, data, updated_at)
                VALUES (:department, CAST(:data AS JSONB), NOW())
                ON CONFLICT (department) DO UPDATE
                SET data = EXCLUDED.data, updated_at = NOW()
                """
            ),
            {"department": dept, "data": empty_payload},
        )
    await db_session.commit()
    await get_cache().clear()

    response = await async_client.get(f"/api/v1/feed/all-sections?department={dept}")
    assert response.status_code == 200
    data = response.json()["data"]

    assert any(item["title"] == "Cached fallback item" for item in data["department"])
