"""Unified AI provider - automatically selects best available service."""

import hashlib
from typing import List

from app.config import settings


class AIProvider:
    """Unified AI provider - automatically selects best available service."""
    
    PRIORITY = [
        ("Gemini", "GEMINI_API_KEY"),
        ("Groq", "GROQ_API_KEY"),
        ("OpenAI", "OPENAI_API_KEY"),
        ("HuggingFace", "HUGGINGFACE_API_KEY"),
        ("Free", None),  # No API key needed
        ("Mock", None),  # Fallback
    ]
    
    def __init__(self):
        self.provider = None
        self.service = None
        
        # Try providers in priority order
        for provider_name, key_name in self.PRIORITY:
            if key_name and getattr(settings, key_name, None):
                # Provider with API key configured
                if provider_name == "Gemini":
                    from app.integrations.gemini_service import GeminiService
                    self.service = GeminiService()
                    self.provider = "Gemini Flash"
                    break
                elif provider_name == "Groq":
                    from app.integrations.groq_service import GroqService
                    self.service = GroqService()
                    self.provider = "Groq (Free Tier)"
                    break
                elif provider_name == "OpenAI":
                    from app.integrations.openai_service import OpenAIService
                    self.service = OpenAIService()
                    self.provider = "OpenAI"
                    break
                elif provider_name == "HuggingFace":
                    from app.integrations.huggingface_service import HuggingFaceService
                    self.service = HuggingFaceService()
                    self.provider = "Hugging Face"
                    break
            elif provider_name == "Free":
                # Try free services
                from app.integrations.free_ai_service import FreeAIService
                self.service = FreeAIService()
                self.provider = "Pollinations AI (Free, No Signup)"
                break
            elif provider_name == "Mock":
                # Final fallback
                from app.integrations.free_ai_service import MockAIService
                self.service = MockAIService()
                self.provider = "Mock (Demo Mode)"
                break
    
    async def summarize(self, title: str, content: str, category: str = "tech") -> dict:
        """Summarize content, returning cached result when available.

        Cache key is derived from a hash of (title + content + category).
        AI summaries are immutable for the same input so TTL is 24 hours.
        """
        from app.services.cache_service import get_cache  # lazy to avoid circular import
        cache = get_cache()
        content_hash = hashlib.md5(
            f"{title}|{content[:3000]}|{category}".encode()
        ).hexdigest()
        cache_key = f"ai:summarize:{content_hash}"

        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self.service.summarize_content(title, content, category)

        if result:
            await cache.set(cache_key, result, 86400)  # 24h TTL
        return result
    
    async def headline(self, title: str, content: str) -> str:
        """Generate headline, returning cached result when available."""
        from app.services.cache_service import get_cache  # lazy to avoid circular import
        cache = get_cache()
        content_hash = hashlib.md5(
            f"{title}|{content[:2000]}".encode()
        ).hexdigest()
        cache_key = f"ai:headline:{content_hash}"

        cached = await cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self.service.generate_headline(title, content)

        if result:
            await cache.set(cache_key, result, 86400)  # 24h TTL
        return result
    
    async def breaking_headline(self, title: str, content: str, source: str = "") -> str:
        """Generate breaking news headline with urgency.
        
        Uses specialized prompting for breaking news that:
        - Creates urgency and immediacy
        - Uses powerful action words
        - Keeps it concise (under 8 words)
        - Maintains factual accuracy while being exciting
        """
        # Check if the service has the specialized breaking headline method
        if hasattr(self.service, 'generate_breaking_headline'):
            return await self.service.generate_breaking_headline(title, content, source)
        else:
            # Fallback to regular headline without forced urgency.
            return await self.service.generate_headline(title, content[:500])
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding."""
        if hasattr(self.service, 'generate_embedding'):
            return await self.service.generate_embedding(text)
        return []
    
    def get_provider_name(self) -> str:
        """Get current provider name."""
        return self.provider
    
    async def close(self):
        """Close services."""
        if self.service and hasattr(self.service, 'close'):
            await self.service.close()


async def check_ai_status() -> dict:
    """Check AI service status - tries all providers."""
    
    # Check Gemini
    if getattr(settings, 'GEMINI_API_KEY', None):
        from app.integrations.gemini_service import check_gemini_status
        return await check_gemini_status(
            settings.GEMINI_API_KEY,
            getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
        )
    
    # Check Groq
    if getattr(settings, 'GROQ_API_KEY', None):
        from app.integrations.groq_service import check_groq_status
        return await check_groq_status(settings.GROQ_API_KEY)
    
    # Check OpenAI
    if getattr(settings, 'OPENAI_API_KEY', None):
        try:
            from app.integrations.openai_service import OpenAIService
            service = OpenAIService()
            response = await service.client.get("/models")
            await service.close()
            
            if response.status_code == 200:
                return {
                    "status": "ready",
                    "provider": "OpenAI",
                    "message": "OpenAI API is configured and working"
                }
        except Exception as e:
            return {
                "status": "error",
                "provider": "OpenAI",
                "message": str(e)
            }
    
    # Check Hugging Face
    if getattr(settings, 'HUGGINGFACE_API_KEY', None):
        from app.integrations.huggingface_service import check_hf_status
        return await check_hf_status(settings.HUGGINGFACE_API_KEY)
    
    # Check Ollama
    if getattr(settings, 'USE_LOCAL_AI', False):
        from app.integrations.ollama import check_ollama_status
        return await check_ollama_status()
    
    # Check free services
    from app.integrations.free_ai_service import check_free_ai_status
    return await check_free_ai_status()


def get_ai_provider_options() -> dict:
    """Get available AI provider options."""
    options = []
    
    if getattr(settings, 'GEMINI_API_KEY', None):
        options.append({
            "name": "Gemini",
            "status": "configured",
            "speed": "Very Fast",
            "cost": "Free tier (1500 req/day)"
        })
    else:
        options.append({
            "name": "Gemini",
            "status": "available",
            "speed": "Very Fast",
            "cost": "Free tier",
            "setup_url": "https://aistudio.google.com/apikey"
        })
    
    if getattr(settings, 'GROQ_API_KEY', None):
        options.append({
            "name": "Groq",
            "status": "configured",
            "speed": "Very Fast",
            "cost": "Free tier"
        })
    else:
        options.append({
            "name": "Groq",
            "status": "available",
            "speed": "Very Fast",
            "cost": "Free tier",
            "setup_url": "https://console.groq.com/"
        })
    
    if getattr(settings, 'OPENAI_API_KEY', None):
        options.append({
            "name": "OpenAI",
            "status": "configured",
            "speed": "Fast",
            "cost": "Pay per use"
        })
    else:
        options.append({
            "name": "OpenAI",
            "status": "available",
            "speed": "Fast",
            "cost": "$5-20/month",
            "setup_url": "https://platform.openai.com/"
        })
    
    if getattr(settings, 'HUGGINGFACE_API_KEY', None):
        options.append({
            "name": "Hugging Face",
            "status": "configured",
            "speed": "Medium",
            "cost": "Free tier"
        })
    else:
        options.append({
            "name": "Hugging Face",
            "status": "available",
            "speed": "Medium",
            "cost": "Free",
            "setup_url": "https://huggingface.co/settings/tokens"
        })
    
    options.append({
        "name": "Pollinations AI",
        "status": "always_available",
        "speed": "Medium",
        "cost": "FREE - No signup!"
    })
    
    if getattr(settings, 'USE_LOCAL_AI', False):
        options.append({
            "name": "Ollama (Local)",
            "status": "configured",
            "speed": "Slow",
            "cost": "Free (uses your CPU)"
        })
    else:
        options.append({
            "name": "Ollama (Local)",
            "status": "available",
            "speed": "Slow",
            "cost": "Free",
            "setup_docs": "docs/OLLAMA_SETUP.md"
        })
    
    # Determine which one will be used
    active = None
    if getattr(settings, 'GEMINI_API_KEY', None):
        active = "Gemini"
    elif getattr(settings, 'GROQ_API_KEY', None):
        active = "Groq"
    elif getattr(settings, 'OPENAI_API_KEY', None):
        active = "OpenAI"
    elif getattr(settings, 'HUGGINGFACE_API_KEY', None):
        active = "Hugging Face"
    elif getattr(settings, 'USE_LOCAL_AI', False):
        active = "Ollama"
    else:
        active = "Pollinations AI (Free)"
    
    return {
        "providers": options,
        "active": active,
        "recommendation": "Gemini Flash is active — fast, free, generous limits"
    }
