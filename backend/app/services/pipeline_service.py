"""Content pipeline orchestrator - manages the full content processing workflow."""

from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.content_processor import ContentProcessor
from app.services.vector_service import VectorService


class PipelineService:
    """Orchestrates the full content processing pipeline."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.content_processor = ContentProcessor(db)
        self.vector_service = VectorService(db)
    
    async def run_full_pipeline(
        self,
        scrape_limit: int = 10,
        process_limit: int = 10,
        embed_limit: int = 10
    ) -> Dict:
        """Run the complete content pipeline."""
        
        results = {
            "scraping": {"status": "skipped", "details": {}},
            "processing": {"status": "pending", "details": {}},
            "vectorization": {"status": "pending", "details": {}},
            "feed_update": {"status": "pending", "details": {}}
        }
        
        # Step 1: Process pending raw content
        print("[Pipeline] Processing raw content...")
        processing_result = await self.content_processor.process_pending_items(
            limit=process_limit
        )
        results["processing"] = {
            "status": "completed",
            "details": processing_result
        }
        
        # Step 2: Generate embeddings for new content
        print("[Pipeline] Generating embeddings...")
        embedding_result = await self.vector_service.embed_pending_content(
            limit=embed_limit
        )
        results["vectorization"] = {
            "status": "completed",
            "details": embedding_result
        }
        
        # Step 3: Update feed stats
        from app.services.feed_service import FeedService
        feed_service = FeedService(self.db)
        stats = await feed_service.get_feed_stats()
        results["feed_update"] = {
            "status": "completed",
            "details": stats
        }
        
        return {
            "status": "success",
            "results": results
        }
    
    async def process_single_item(self, raw_content_id: str) -> Dict:
        """Process a single raw content item through the full pipeline."""
        
        from app.models import RawContent
        
        # Get raw content
        result = await self.db.execute(
            select(RawContent).where(RawContent.id == raw_content_id)
        )
        raw = result.scalar_one_or_none()
        
        if not raw:
            return {"status": "error", "error": "Content not found"}
        
        # Process
        processed = await self.content_processor.process_single_item(raw)
        
        if not processed:
            return {"status": "error", "error": "Processing failed"}
        
        # Generate embedding
        embedding = await self.vector_service.embed_content(processed)
        
        return {
            "status": "success",
            "content_id": str(processed.id),
            "title": processed.title,
            "attractiveness_score": processed.attractiveness_score,
            "embedding_created": embedding is not None
        }
    
    async def get_pipeline_status(self) -> Dict:
        """Get current pipeline status."""
        
        from app.models import RawContent, ProcessedContent, VectorEmbedding
        
        # Raw content counts
        result = await self.db.execute(
            select(RawContent.status, func.count(RawContent.id))
            .group_by(RawContent.status)
        )
        raw_counts = dict(result.all())
        
        # Processed content count
        result = await self.db.execute(
            select(func.count(ProcessedContent.id))
        )
        processed_count = result.scalar()
        
        # Content without embeddings
        result = await self.db.execute(
            select(func.count(ProcessedContent.id))
            .outerjoin(VectorEmbedding, ProcessedContent.id == VectorEmbedding.content_id)
            .where(VectorEmbedding.id.is_(None))
        )
        pending_embeddings = result.scalar()
        
        # Get AI provider status
        from app.integrations.ai_provider import AIProvider
        ai_provider = AIProvider()
        
        return {
            "raw_content": {
                "pending": raw_counts.get("pending", 0),
                "processed": raw_counts.get("processed", 0),
                "failed": raw_counts.get("failed", 0)
            },
            "processed_content": processed_count,
            "pending_embeddings": pending_embeddings,
            "ai_provider": ai_provider.provider
        }
