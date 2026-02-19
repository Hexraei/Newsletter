"""Daily refresh job: populate Supabase scraped items and refresh ranked cache."""

from __future__ import annotations

import asyncio

from app.main_lite import _load_items_for_feed, supabase_client
from app.ranking_engine import candidate_to_feed_item, rank_all_sections
from populate_supabase_scraped import _populate


async def _refresh_ranked_cache() -> None:
    items = await _load_items_for_feed()
    ranked = rank_all_sections(
        items,
        limits={
            "breaking": 8,
            "department": 3,
            "student_stories": 3,
            "trending": 3,
        },
    )
    payload = {
        "breaking": [candidate_to_feed_item(candidate) for candidate in ranked["breaking"]],
        "department": [candidate_to_feed_item(candidate) for candidate in ranked["department"]],
        "student_stories": [candidate_to_feed_item(candidate) for candidate in ranked["student_stories"]],
        "trending": [candidate_to_feed_item(candidate) for candidate in ranked["trending"]],
    }
    ok = await supabase_client.upsert_ranked_cache(payload)
    print(f"Ranked cache updated: {ok}")


async def main() -> None:
    await _populate()
    await _refresh_ranked_cache()
    print("Daily Supabase refresh completed")


if __name__ == "__main__":
    asyncio.run(main())
