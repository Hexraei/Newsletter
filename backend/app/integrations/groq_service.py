"""Groq integration - FREE fast AI API."""

from typing import List, Optional

import httpx

from app.config import settings


class GroqService:
    """Groq API service - extremely fast, free tier available."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'GROQ_API_KEY', None)
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0  # Groq is very fast
        )
        self.model = "llama-3.2-3b-preview"  # Fast and cheap
    
    async def summarize_content(
        self,
        title: str,
        content: str,
        category: str = "tech"
    ) -> dict:
        """Summarize content using Groq."""
        
        system_prompt = """You are a content summarizer for a college newsletter. 
Convert articles into concise 2-3 minute summaries.

Format:
- Hook: One catchy attention-grabbing sentence
- Why it matters: One line on relevance  
- Key points: 3-6 bullet points
- Action step: One practical takeaway

Keep it brief and engaging."""

        user_prompt = f"""Title: {title}
Category: {category}

Content:
{content[:3000]}

Provide the summary in the specified format."""

        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
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
        
        system_prompt = """Create catchy headlines (max 10 words) for a college newsletter."""

        user_prompt = f"""Original: {title}
Content: {content[:500]}

Create the best headline:"""

        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
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
        return headline.strip('"').strip("'")
    
    def _parse_summary(self, text: str) -> dict:
        """Parse summary text."""
        lines = text.strip().split('\n')
        result = {
            "hook": "",
            "why_it_matters": "",
            "key_points": [],
            "action_step": ""
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower = line.lower()
            
            if 'hook' in lower:
                result['hook'] = line.split(':', 1)[-1].strip()
            elif 'why' in lower and 'matter' in lower:
                result['why_it_matters'] = line.split(':', 1)[-1].strip()
            elif 'action' in lower:
                result['action_step'] = line.split(':', 1)[-1].strip()
            elif line.startswith('-') or line.startswith('•'):
                result['key_points'].append(line.lstrip('- •').strip())
        
        return result
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def check_groq_status(api_key: str) -> dict:
    """Check Groq API status."""
    try:
        client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response = await client.get("https://api.groq.com/openai/v1/models")
        await client.aclose()
        
        if response.status_code == 200:
            return {
                "status": "ready",
                "provider": "Groq",
                "message": "Groq API is configured and working"
            }
        else:
            return {
                "status": "error",
                "provider": "Groq",
                "message": f"Groq API error: {response.status_code}"
            }
    except Exception as e:
        return {
            "status": "error",
            "provider": "Groq",
            "message": str(e)
        }
