"""OpenAI integration for cloud AI."""

from typing import List, Optional

import httpx

from app.config import settings


class OpenAIService:
    """OpenAI API service for content processing."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
    
    async def summarize_content(
        self,
        title: str,
        content: str,
        category: str = "tech"
    ) -> dict:
        """Summarize content using GPT."""
        
        system_prompt = """You are a content summarizer for a college newsletter. 
Convert articles into concise 2-3 minute summaries.

Format:
- Hook: One catchy attention-grabbing sentence
- Why it matters: One line on relevance
- Key points: 3-6 bullet points
- Action step: One practical takeaway

Keep it brief, engaging, student-friendly."""

        user_prompt = f"""Title: {title}
Category: {category}

Content:
{content[:3000]}

Provide the summary in the specified format."""

        response = await self.client.post(
            "/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        response.raise_for_status()
        
        data = response.json()
        summary_text = data["choices"][0]["message"]["content"]
        
        return self._parse_summary(summary_text)
    
    async def generate_headline(self, title: str, content: str) -> str:
        """Generate catchy headline."""
        
        system_prompt = """You are a headline writer for a college tech newsletter.
Create catchy, click-worthy headlines (max 10 words).

Rules:
- Use power words
- Create curiosity
- Keep under 10 words"""

        user_prompt = f"""Original: {title}

Content preview: {content[:500]}

Create the best headline:"""

        response = await self.client.post(
            "/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 50
            }
        )
        response.raise_for_status()
        
        data = response.json()
        headline = data["choices"][0]["message"]["content"].strip()
        
        # Clean up
        headline = headline.strip('"').strip("'")
        return headline
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding."""
        response = await self.client.post(
            "/embeddings",
            json={
                "model": "text-embedding-3-small",
                "input": text[:8000]  # Token limit
            }
        )
        response.raise_for_status()
        
        data = response.json()
        return data["data"][0]["embedding"]
    
    def _parse_summary(self, text: str) -> dict:
        """Parse summary text."""
        lines = text.strip().split('\n')
        result = {
            "hook": "",
            "why_it_matters": "",
            "key_points": [],
            "action_step": ""
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower = line.lower()
            
            if 'hook' in lower:
                current_section = 'hook'
                result['hook'] = line.split(':', 1)[-1].strip()
            elif 'why' in lower and 'matter' in lower:
                current_section = 'why'
                result['why_it_matters'] = line.split(':', 1)[-1].strip()
            elif 'action' in lower or 'takeaway' in lower:
                current_section = 'action'
                result['action_step'] = line.split(':', 1)[-1].strip()
            elif line.startswith('-') or line.startswith('•'):
                result['key_points'].append(line.lstrip('- •').strip())
        
        return result
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class AIProvider:
    """Unified AI provider - uses OpenAI or Ollama."""
    
    def __init__(self):
        self.use_openai = bool(settings.OPENAI_API_KEY)
        self.openai_service = None
        self.ollama_service = None
        
        if self.use_openai:
            self.openai_service = OpenAIService()
        else:
            from app.integrations.ollama import LocalNLPService
            self.ollama_service = LocalNLPService()
    
    async def summarize(self, title: str, content: str, category: str = "tech") -> dict:
        """Summarize content."""
        if self.openai_service:
            return await self.openai_service.summarize_content(title, content, category)
        else:
            return await self.ollama_service.summarize_content(title, content, category)
    
    async def headline(self, title: str, content: str) -> str:
        """Generate headline."""
        if self.openai_service:
            return await self.openai_service.generate_headline(title, content)
        else:
            return await self.ollama_service.generate_headline(title, content)
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding."""
        if self.openai_service:
            return await self.openai_service.generate_embedding(text)
        else:
            return await self.ollama_service.generate_embedding(text)
    
    def get_provider_name(self) -> str:
        """Get current provider name."""
        return "OpenAI" if self.openai_service else "Ollama (Local)"
    
    async def close(self):
        """Close services."""
        if self.openai_service:
            await self.openai_service.close()


async def check_ai_status() -> dict:
    """Check AI service status."""
    
    # Check OpenAI
    if settings.OPENAI_API_KEY:
        try:
            service = OpenAIService()
            # Quick test
            response = await service.client.get("/models")
            if response.status_code == 200:
                await service.close()
                return {
                    "status": "ready",
                    "provider": "OpenAI",
                    "message": "OpenAI API is configured and working"
                }
        except Exception as e:
            return {
                "status": "error",
                "provider": "OpenAI",
                "message": f"OpenAI API error: {str(e)}"
            }
    
    # Check Ollama
    else:
        from app.integrations.ollama import check_ollama_status
        return await check_ollama_status()
