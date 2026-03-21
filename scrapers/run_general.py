"""Run scrapers and process content directly (no auth required)."""
import argparse
import asyncio
import os
import sys
from time import perf_counter

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "backend"))
sys.path.insert(0, _root)  # for scrapers.lib imports

from dotenv import load_dotenv
load_dotenv(os.path.join(_root, "backend", ".env"))

from app.models.base import AsyncSessionLocal
from app.departments import INDIA_COMMON_REDDIT
from app.services.scraper_service import ScraperService
from app.services.content_processor import ContentProcessor


PROFILE_DEFAULTS = {
    "speed": {
        "process_limit": 30,
        "process_concurrency": 4,
        "progress_every": 10,
        "scrapers": {
            "hackernews": {"limit": 20, "timeout": 45},
            "reddit": {"limit": 12, "timeout": 75},
            "github": {"limit": 10, "timeout": 45},
            "medium": {"limit": 8, "timeout": 45},
            "producthunt": {"limit": 8, "timeout": 45},
        },
    },
    "balanced": {
        "process_limit": 60,
        "process_concurrency": 3,
        "progress_every": 10,
        "scrapers": {
            "hackernews": {"limit": 30, "timeout": 60},
            "reddit": {"limit": 18, "timeout": 120},
            "github": {"limit": 15, "timeout": 60},
            "medium": {"limit": 15, "timeout": 60},
            "producthunt": {"limit": 15, "timeout": 60},
        },
    },
    "quality": {
        "process_limit": 100,
        "process_concurrency": 1,
        "progress_every": 10,
        "scrapers": {
            "hackernews": {"limit": 30, "timeout": 90},
            "reddit": {"limit": 25, "timeout": 180},
            "github": {"limit": 20, "timeout": 90},
            "medium": {"limit": 20, "timeout": 90},
            "producthunt": {"limit": 20, "timeout": 90},
        },
    },
    "india_strict": {
        "process_limit": 120,
        "process_concurrency": 1,
        "progress_every": 10,
        "scrapers": {
            "reddit": {"limit": 20, "timeout": 180},
            "hackernews": {"limit": 8, "timeout": 45},
            "github": {"limit": 6, "timeout": 45},
            "medium": {"limit": 6, "timeout": 45},
            "producthunt": {"limit": 6, "timeout": 45},
        },
    },
}


async def _run_scraper_with_timeout(service: ScraperService, name: str, timeout_seconds: int, **kwargs):
    try:
        return await asyncio.wait_for(service.run_scraper(name, **kwargs), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return {
            "scraper": name,
            "status": "failed",
            "error": f"Timed out after {timeout_seconds}s",
            "items_scraped": 0,
            "items_stored": 0,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run general scraping and processing pipeline.")
    parser.add_argument(
        "--mode",
        choices=["speed", "balanced", "quality", "india_strict"],
        default="india_strict",
        help="Pipeline mode profile. Defaults to india_strict.",
    )
    parser.add_argument(
        "--process-limit",
        type=int,
        default=None,
        help="Override number of pending items to process.",
    )
    parser.add_argument(
        "--skip-processing",
        action="store_true",
        help="Run scrapers only; skip pending content processing.",
    )
    parser.add_argument(
        "--include-global-fallback",
        action="store_true",
        help=(
            "In india_strict mode, also run global fallback scrapers "
            "(hackernews/github/medium/producthunt)."
        ),
    )
    return parser.parse_args()


def _india_reddit_subreddits() -> list[str]:
    return list(INDIA_COMMON_REDDIT)


async def main(args: argparse.Namespace):
    started_at = perf_counter()
    profile = PROFILE_DEFAULTS[args.mode]
    process_limit = args.process_limit if args.process_limit is not None else profile["process_limit"]

    async with AsyncSessionLocal() as db:
        service = ScraperService(db)
        await service.ensure_sources_exist()
        scrape_started_at = perf_counter()
        scrape_results = {}

        if args.mode == "india_strict":
            print("\n--- Running RSS stage (India/TN focused sources) ---")
            rss_started_at = perf_counter()
            from scrapers.run_rss import main as run_rss_main, run_department_knowledge_stage
            await run_rss_main(only_india=True)
            print("\n--- Running RSS knowledge stage (department growth/tech sources) ---")
            await run_department_knowledge_stage()
            print(f"[Timing] RSS stage: {perf_counter() - rss_started_at:.2f}s")

        # Run scrapers that work without API keys.
        # In strict mode, default to India-focused ingestion for better precision + latency.
        if args.mode == "india_strict":
            scraper_order = ["reddit"]
            if args.include_global_fallback:
                scraper_order.extend(["hackernews", "github", "medium", "producthunt"])
        else:
            scraper_order = ["hackernews", "reddit", "github", "medium", "producthunt"]
        india_reddit_subs = _india_reddit_subreddits() if args.mode == "india_strict" else None

        for name in scraper_order:
            scraper_defaults = profile["scrapers"][name]
            scraper_kwargs = {
                "mode": args.mode,
                "limit": scraper_defaults["limit"],
            }
            if args.mode == "india_strict" and name == "reddit":
                scraper_kwargs["subreddits"] = india_reddit_subs
            print(f"\n--- Running {name} scraper ---")
            result = await _run_scraper_with_timeout(
                service,
                name,
                timeout_seconds=scraper_defaults["timeout"],
                **scraper_kwargs,
            )
            print(f"  Result: {result}")
            scrape_results[name] = result

        scrape_duration = perf_counter() - scrape_started_at
        total_scraped = sum((r.get("items_scraped") or 0) for r in scrape_results.values() if isinstance(r, dict))
        total_stored = sum((r.get("items_stored") or 0) for r in scrape_results.values() if isinstance(r, dict))
        print(f"\n[Timing] Scrape stage: {scrape_duration:.2f}s")
        print(f"[Summary] Scraped: {total_scraped} | Stored: {total_stored}")

        # Process pending content
        if args.skip_processing:
            print("\n--- Skipping pending content processing (--skip-processing) ---")
        else:
            process_started_at = perf_counter()
            print("\n--- Processing pending content ---")
            processor = ContentProcessor(db)
            processed = await processor.process_pending_items(
                limit=process_limit,
                mode=args.mode,
                concurrency=profile["process_concurrency"],
                progress_every=profile["progress_every"],
            )
            process_duration = perf_counter() - process_started_at
            print(f"  Processed {processed}")
            print(f"[Timing] Process stage: {process_duration:.2f}s")

    total_duration = perf_counter() - started_at
    print(f"[Timing] Total run duration: {total_duration:.2f}s")


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
