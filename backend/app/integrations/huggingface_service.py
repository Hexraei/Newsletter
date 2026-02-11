"""Hugging Face Inference API - FREE tier available."""

from typing import List

import httpx

from app.config import settings


class HuggingFaceService:
    """Hugging Face Inference API - free tier available."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'HUGGINGFACE_API_KEY', None)
        self.base_url = "https://api-inference.huggingface.co/models"
        
        # Free models that work well
        self.summarization_model = "facebook/bart-large-cnn"
        self.generation_model = "HuggingFaceH4/zephyr-7b-beta"
        self.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    
    async def _query(self, model: str, payload: dict) -> dict:
        """Query Hugging Face API."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/{model}",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code == 503:
                # Model is loading
                return {"error": "Model is loading, try again in a few seconds"}
            
            response.raise_for_status()
            return response.json()
    
    async def summarize_content(self, title: str, content: str, category: str = "tech") -> dict:
        """Summarize content."""
        text = f"{title}\n\n{content}"
        
        try:
            result = await self._query(
                self.summarization_model,
                {"inputs": text[:1024], "parameters": {"max_length": 150, "min_length": 30}}
            )
            
            summary_text = result[0]["summary_text"] if isinstance(result, list) else str(result)
            
            return {
                "hook": title,
                "why_it_matters": "Relevant for students",
                "key_points": summary_text[:200].split(". ")[:4],
                "action_step": "Stay updated with this trend"
            }
        except Exception as e:
            # Fallback to basic extraction
            return self._basic_summarize(title, content)
    
    async def generate_headline(self, title: str, content: str) -> str:
        """Generate headline."""
        prompt = f"Create a catchy headline for: {title}"
        
        try:
            result = await self._query(
                self.generation_model,
                {
                    "inputs": prompt,
                    "parameters": {"max_new_tokens": 20, "temperature": 0.7}
                }
            )
            
            if isinstance(result, list) and len(result) > 0:
                generated = result[0].get("generated_text", title)
                return generated.strip().strip('"').strip("'")[:100]
            return title
        except Exception:
            return title
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding."""
        try:
            result = await self._query(
                self.embedding_model,
                {"inputs": text}
            )
            
            if isinstance(result, list):
                return result[0] if isinstance(result[0], list) else result
            return []
        except Exception:
            return []
    
    def _basic_summarize(self, title: str, content: str) -> dict:
        """Basic fallback summarization."""
        sentences = content.split(". ")[:5]
        return {
            "hook": title,
            "why_it_matters": "Important for students to know",
            "key_points": [s.strip() for s in sentences if len(s) > 20][:4],
            "action_step": "Consider how this affects your studies"
        }


async def check_hf_status(api_key: str = None) -> dict:
    """Check Hugging Face API status."""
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        async with httpx.AsyncClient() as client:
            # Try to query a simple model
            response = await client.post(
                "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
                headers=headers,
                json={"inputs": "Test"},
                timeout=10.0
            )
            
            if response.status_code in [200, 503]:  # 503 means model loading, which is OK
                return {
                    "status": "ready",
                    "provider": "Hugging Face",
                    "message": "Hugging Face API is accessible" + (" (authenticated)" if api_key else " (anonymous)")
                }
            else:
                return {
                    "status": "error",
                    "provider": "Hugging Face",
                    "message": f"API returned {response.status_code}"
                }
    except Exception as e:
        return {
            "status": "error",
            "provider": "Hugging Face",
            "message": str(e)
        }
