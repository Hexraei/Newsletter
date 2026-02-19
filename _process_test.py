"""Temp: Process remaining Reddit items + inspect AI results."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_platform"))

async def run():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select, desc, text
    from app.models.base import Base
    from app.models import ProcessedContent, RawContent, Source
    from app.services.content_processor import ContentProcessor
    from app.integrations.ai_provider import AIProvider

    engine = create_async_engine(
        "postgresql+asyncpg://postgres:newsletter123@localhost:5432/newsletter", echo=False
    )
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        ai = AIProvider()
        print(f"AI Provider: {ai.provider}\n")

        processor = ContentProcessor(db)

        # Process all remaining pending (should include Reddit + GitHub high-score items)
        print("Processing 15 more pending items...")
        result = await processor.process_pending_items(limit=15)
        print(f"Result: processed={result['processed']}, errors={len(result['errors'])}")
        if result["errors"]:
            for e in result["errors"][:5]:
                print(f"  ERROR: {e}")

        # Show only items that went through NLP (score >= 60, type=news)
        print("\n" + "=" * 70)
        print("AI-PROCESSED ITEMS (score >= 60, content_type=news)")
        print("=" * 70)

        rows = await db.execute(
            select(ProcessedContent)
            .where(ProcessedContent.content_type == "news")
            .order_by(desc(ProcessedContent.attractiveness_score))
        )
        nlp_items = rows.scalars().all()

        if not nlp_items:
            print("  (none yet — checking all high-score items instead)")
            rows = await db.execute(
                select(ProcessedContent)
                .where(ProcessedContent.attractiveness_score >= 60)
                .order_by(desc(ProcessedContent.attractiveness_score))
            )
            nlp_items = rows.scalars().all()

        for i, item in enumerate(nlp_items):
            print(f"\n--- [{i+1}] Score: {item.attractiveness_score} | Type: {item.content_type} | Breaking: {item.is_breaking} ---")
            print(f"Title:    {(item.title or 'N/A')[:80]}")
            print(f"Category: {item.category} | Topics: {item.topic_tags}")

            summary = item.summary or ""
            print(f"Summary:  {summary[:250]}")

            blocks = item.content_blocks or {}
            hook = blocks.get("hook", "")
            if hook:
                print(f"Hook:     {hook[:150]}")

            kp = blocks.get("key_points", [])
            if kp:
                print(f"Key Points ({len(kp)}):")
                for j, pt in enumerate(kp[:5]):
                    pt_text = pt if isinstance(pt, str) else str(pt)
                    print(f"  {j+1}. {pt_text[:100]}")

            action = blocks.get("action_step", "")
            if action:
                print(f"Action:   {action[:150]}")

            if item.featured_image_url:
                print(f"Image:    {item.featured_image_url[:80]}")

        # Final stats
        print("\n" + "=" * 70)
        print("FINAL STATS")
        r = await db.execute(text(
            "SELECT content_type, COUNT(*), AVG(attractiveness_score)::int "
            "FROM processed_content GROUP BY content_type"
        ))
        for row in r.fetchall():
            print(f"  {row[0]}: {row[1]} items, avg score {row[2]}")

        r2 = await db.execute(text("SELECT COUNT(*) FROM raw_content WHERE status = 'pending'"))
        pending = r2.scalar()
        r3 = await db.execute(text("SELECT COUNT(*) FROM processed_content"))
        total_proc = r3.scalar()
        print(f"\n  Total processed: {total_proc}")
        print(f"  Still pending:   {pending}")

    await engine.dispose()

asyncio.run(run())
