"""Vector embedding service for content similarity search."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ai_provider import AIProvider
from app.models import ProcessedContent, VectorEmbedding


class VectorService:
    """Service for generating and managing vector embeddings."""
    
    # Embedding dimensions by model
    EMBEDDING_DIMS = {
        "ollama-nomic": 768,
        "ollama-mxbai": 1024,
        "mock": 384,
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_provider = AIProvider()
        self.model_version = self._detect_model()
    
    def _detect_model(self) -> str:
        """Detect which embedding model to use."""
        provider = self.ai_provider.provider
        
        if "Ollama" in provider:
            return "ollama-nomic"
        elif "Mock" in provider:
            return "mock"
        else:
            return "default"
    
    async def embed_content(self, content: ProcessedContent) -> Optional[VectorEmbedding]:
        """Generate embedding for processed content."""
        
        # Prepare text for embedding
        text_to_embed = f"{content.title} {content.summary or ''}"
        text_to_embed = " ".join(text_to_embed.split()[:500])  # Limit tokens
        
        # Generate embedding
        embedding_vector = await self.ai_provider.embed(text_to_embed)
        
        if not embedding_vector:
            # No embedding available, skip
            return None
        
        # Create embedding record
        vector_embedding = VectorEmbedding(
            content_id=content.id,
            embedding=embedding_vector,
            model_version=self.model_version
        )
        
        self.db.add(vector_embedding)
        await self.db.commit()
        await self.db.refresh(vector_embedding)
        
        return vector_embedding
    
    async def embed_pending_content(self, limit: int = 10) -> dict:
        """Generate embeddings for content without embeddings."""
        
        # Find content without embeddings
        result = await self.db.execute(
            select(ProcessedContent)
            .outerjoin(VectorEmbedding, ProcessedContent.id == VectorEmbedding.content_id)
            .where(VectorEmbedding.id.is_(None))
            .limit(limit)
        )
        pending = result.scalars().all()
        
        embedded_count = 0
        skipped_count = 0
        
        for content in pending:
            embedding = await self.embed_content(content)
            if embedding:
                embedded_count += 1
            else:
                skipped_count += 1
        
        return {
            "embedded": embedded_count,
            "skipped": skipped_count,
            "total_pending": len(pending)
        }
    
    async def find_similar_content(
        self,
        content_id: str,
        limit: int = 5
    ) -> List[dict]:
        """Find similar content using vector similarity."""
        
        # Get the content's embedding
        result = await self.db.execute(
            select(VectorEmbedding)
            .where(VectorEmbedding.content_id == content_id)
        )
        source_embedding = result.scalar_one_or_none()
        
        if not source_embedding:
            return []
        
        # Simple cosine similarity using Python
        # In production, use pgvector for efficient similarity search
        source_vector = source_embedding.embedding
        
        result = await self.db.execute(
            select(VectorEmbedding, ProcessedContent)
            .join(ProcessedContent, VectorEmbedding.content_id == ProcessedContent.id)
            .where(VectorEmbedding.content_id != content_id)
        )
        all_embeddings = result.all()
        
        # Calculate similarities
        similarities = []
        for vec_embed, proc_content in all_embeddings:
            similarity = self._cosine_similarity(source_vector, vec_embed.embedding)
            similarities.append((similarity, proc_content))
        
        # Sort by similarity and return top results
        similarities.sort(reverse=True, key=lambda x: x[0])
        
        return [
            {
                "content_id": str(item.id),
                "title": item.title,
                "similarity": round(score, 3),
                "category": item.category
            }
            for score, item in similarities[:limit]
        ]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    async def search_by_text(self, query: str, limit: int = 10) -> List[dict]:
        """Search content by text similarity."""
        
        # Generate embedding for query
        query_embedding = await self.ai_provider.embed(query)
        
        if not query_embedding:
            # Fallback to text search
            result = await self.db.execute(
                select(ProcessedContent)
                .where(ProcessedContent.title.ilike(f"%{query}%"))
                .limit(limit)
            )
            items = result.scalars().all()
            return [
                {
                    "content_id": str(item.id),
                    "title": item.title,
                    "category": item.category,
                    "similarity": 1.0
                }
                for item in items
            ]
        
        # Vector similarity search
        result = await self.db.execute(
            select(VectorEmbedding, ProcessedContent)
            .join(ProcessedContent, VectorEmbedding.content_id == ProcessedContent.id)
        )
        all_embeddings = result.all()
        
        # Calculate similarities
        similarities = []
        for vec_embed, proc_content in all_embeddings:
            similarity = self._cosine_similarity(query_embedding, vec_embed.embedding)
            similarities.append((similarity, proc_content))
        
        # Sort by similarity
        similarities.sort(reverse=True, key=lambda x: x[0])
        
        return [
            {
                "content_id": str(item.id),
                "title": item.title,
                "category": item.category,
                "similarity": round(score, 3)
            }
            for score, item in similarities[:limit]
        ]
