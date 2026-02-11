"""Free AI services requiring NO signup or API keys."""

from typing import List

import httpx


class FreeAIService:
    """Free AI service using Pollinations AI (no signup required)."""
    
    def __init__(self):
        self.base_url = "https://text.pollinations.ai"
    
    async def _generate(self, prompt: str, system: str = None, seed: int = 42) -> str:
        """Generate text using Pollinations AI (completely free)."""
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "messages": messages,
            "seed": seed,
            "model": "openai"  # Uses GPT-3.5-turbo for free
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/openai",
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def summarize_content(self, title: str, content: str, category: str = "tech") -> dict:
        """Summarize content."""
        
        system = """You summarize news for college students. Format:
Hook: One catchy sentence
Why it matters: One line
Key points: 3-5 bullet points
Action step: One practical takeaway

Be concise and engaging."""

        prompt = f"Title: {title}\n\nContent: {content[:2000]}\n\nProvide summary in the specified format."
        
        try:
            response = await self._generate(prompt, system)
            return self._parse_summary(response)
        except Exception as e:
            # Fallback
            return self._basic_summarize(title, content)
    
    async def generate_headline(self, title: str, content: str) -> str:
        """Generate catchy headline."""
        
        system = "Create catchy, click-worthy headlines under 10 words."
        prompt = f"Original title: {title}\n\nCreate a catchy headline:"
        
        try:
            response = await self._generate(prompt, system)
            return response.strip().strip('"').strip("'")[:100]
        except Exception:
            return title
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding (not available in free tier)."""
        return []
    
    def _parse_summary(self, text: str) -> dict:
        """Parse summary from AI response."""
        result = {
            "hook": "",
            "why_it_matters": "",
            "key_points": [],
            "action_step": ""
        }
        
        lines = text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower = line.lower()
            
            if 'hook' in lower:
                result['hook'] = line.split(':', 1)[-1].strip()
                current_section = 'hook'
            elif 'why' in lower and 'matter' in lower:
                result['why_it_matters'] = line.split(':', 1)[-1].strip()
                current_section = 'why'
            elif 'action' in lower or 'takeaway' in lower or 'step' in lower:
                result['action_step'] = line.split(':', 1)[-1].strip()
                current_section = 'action'
            elif line.startswith('-') or line.startswith('•') or 'key' in lower:
                point = line.lstrip('- •').strip()
                if point and len(point) > 5:
                    result['key_points'].append(point)
        
        # Fallbacks
        if not result['hook']:
            result['hook'] = "Breaking: Important update for students"
        if not result['why_it_matters']:
            result['why_it_matters'] = "This affects your academic and career journey"
        if not result['key_points']:
            result['key_points'] = ["Important development", "Students should be aware"]
        if not result['action_step']:
            result['action_step'] = "Stay informed and share with peers"
        
        return result
    
    def _basic_summarize(self, title: str, content: str) -> dict:
        """Basic fallback summarization."""
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20][:4]
        return {
            "hook": title,
            "why_it_matters": "Relevant for college students",
            "key_points": sentences if sentences else ["Key information available"],
            "action_step": "Consider implications for your studies"
        }


class MockAIService:
    """Mock AI service for testing without any external calls."""
    
    async def summarize_content(self, title: str, content: str, category: str = "tech") -> dict:
        """Return mock summary."""
        return {
            "hook": f"🚀 {title[:50]}...",
            "why_it_matters": "This development could impact your academic journey and future career opportunities.",
            "key_points": [
                "Key development in the field",
                "Students should stay informed",
                "May affect job market trends",
                "Opportunity for skill development"
            ],
            "action_step": "Research more about this topic and discuss with peers"
        }
    
    async def generate_headline(self, title: str, content: str) -> str:
        """Return mock headline."""
        return f"🔥 {title}"
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Return mock embedding."""
        return [0.1] * 384  # Mock 384-dim embedding


async def check_free_ai_status() -> dict:
    """Check free AI service status."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://text.pollinations.ai/models",
                timeout=10.0
            )
            
            if response.status_code == 200:
                return {
                    "status": "ready",
                    "provider": "Pollinations AI (Free)",
                    "message": "Free AI service is available - no signup required!"
                }
            else:
                return {
                    "status": "degraded",
                    "provider": "Pollinations AI",
                    "message": "Service may be slow, but should work"
                }
    except Exception as e:
        return {
            "status": "fallback",
            "provider": "Mock AI",
            "message": "Free service unavailable, using mock responses for testing"
        }
