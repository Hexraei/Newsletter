"""Free AI services requiring NO signup or API keys."""

import json
import re
from typing import Any, List

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
        """Summarize content with content-first approach."""

        system = """You are summarizing a news article for college students.

Extract the core information from the article. Do not invent or assume anything not stated in the text.

Return ONLY valid JSON:
{
  "what_happened": "1-2 plain sentences stating the main event. Include who, what, when if available.",
  "why_it_matters": "1-2 sentences on concrete impact — on jobs, technology, industry, or academics. Be specific.",
  "key_facts": ["3-5 specific facts from the article: numbers, names, dates, companies, technologies. Only facts explicitly stated."]
}

Rules:
- No markdown, no code fences, no extra keys.
- Never use filler phrases like 'stay informed', 'this is important', 'in today's rapidly evolving world'.
- If the article lacks substance for key_facts, return fewer bullets rather than padding with vague statements.
- Ground every sentence in the provided text."""

        prompt = (
            f"Title: {title}\n"
            f"Category: {category}\n\n"
            f"Content:\n{content[:3000]}\n\n"
            "Extract the core information as JSON."
        )
        
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
    
    def _clean_line(self, value: Any, max_len: int = 240) -> str:
        text = str(value or "").replace("\n", " ").strip()
        text = re.sub(r"\s+", " ", text)
        text = text.strip(" -*•\t")
        if len(text) > max_len:
            text = text[: max_len - 3].rstrip() + "..."
        return text

    def _extract_json_object(self, text: str) -> dict | None:
        raw = text.strip()
        candidates = [raw]

        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
        if fenced_match:
            candidates.append(fenced_match.group(1))

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(raw[start : end + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue
        return None

    def _normalize_summary(self, payload: dict) -> dict:
        result = {
            "hook": "",
            "why_it_matters": "",
            "key_points": [],
            "action_step": ""
        }

        # Map content-first fields to existing schema
        result["hook"] = self._clean_line(
            payload.get("what_happened") or payload.get("hook")
        )
        result["why_it_matters"] = self._clean_line(
            payload.get("why_it_matters") or payload.get("why")
        )
        result["action_step"] = self._clean_line(
            payload.get("action_step") or payload.get("next_step") or ""
        )

        raw_points = payload.get("key_facts") or payload.get("key_points")
        if isinstance(raw_points, list):
            points = [self._clean_line(point, max_len=160) for point in raw_points]
        elif isinstance(raw_points, str):
            points = [self._clean_line(part, max_len=160) for part in re.split(r"[\n;•-]+", raw_points)]
        else:
            points = []

        result["key_points"] = [point for point in points if len(point) >= 10][:5]
        return result

    def _parse_summary(self, text: str) -> dict:
        """Parse summary from AI response."""
        parsed_json = self._extract_json_object(text)
        if parsed_json:
            result = self._normalize_summary(parsed_json)
            # Accept if we got the core fields (what_happened/hook + key_facts/key_points)
            if result["hook"] and (result["key_points"] or result["why_it_matters"]):
                return result

        result = {
            "hook": "",
            "why_it_matters": "",
            "key_points": [],
            "action_step": ""
        }

        lines = text.strip().split('\n')
        current_section = None

        for line in lines:
            line = self._clean_line(line)
            if not line:
                continue

            lower = line.lower()

            if 'hook' in lower or 'quick summary' in lower or lower.startswith('summary:'):
                result['hook'] = self._clean_line(line.split(':', 1)[-1])
                current_section = 'hook'
            elif ('why' in lower and 'matter' in lower) or 'why important' in lower:
                result['why_it_matters'] = self._clean_line(line.split(':', 1)[-1])
                current_section = 'why'
            elif 'action' in lower or 'takeaway' in lower or 'step' in lower or 'how it affects' in lower:
                result['action_step'] = self._clean_line(line.split(':', 1)[-1])
                current_section = 'action'
            elif line.startswith('-') or line.startswith('•') or 'key' in lower:
                point = self._clean_line(line.lstrip('- •'), max_len=160)
                if point and len(point) > 5:
                    result['key_points'].append(point)
            elif current_section == 'hook' and not result['hook']:
                result['hook'] = self._clean_line(line)
            elif current_section == 'why' and not result['why_it_matters']:
                result['why_it_matters'] = self._clean_line(line)
            elif current_section == 'action' and not result['action_step']:
                result['action_step'] = self._clean_line(line)
        
        # Fallbacks — use empty strings instead of generic filler
        if not result['hook']:
            result['hook'] = ""
        if not result['why_it_matters']:
            result['why_it_matters'] = ""
        if not result['action_step']:
            result['action_step'] = ""
        
        return result
    
    def _basic_summarize(self, title: str, content: str) -> dict:
        """Basic fallback summarization — extracts actual sentences from content."""
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20][:5]
        return {
            "hook": title,
            "why_it_matters": sentences[0] + "." if sentences else "",
            "key_points": [s + "." for s in sentences[1:4]] if len(sentences) > 1 else [],
            "action_step": ""
        }


class MockAIService:
    """Mock AI service for testing without any external calls."""
    
    async def summarize_content(self, title: str, content: str, category: str = "tech") -> dict:
        """Return mock summary using actual content."""
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20][:5]
        return {
            "hook": title,
            "why_it_matters": sentences[0] + "." if sentences else "",
            "key_points": [s + "." for s in sentences[1:4]] if len(sentences) > 1 else [],
            "action_step": ""
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
