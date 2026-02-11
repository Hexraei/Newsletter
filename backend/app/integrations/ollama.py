"""Ollama integration for local AI models."""

import json
from typing import AsyncGenerator, List, Optional

import httpx

from app.config import settings


class OllamaClient:
    """Client for Ollama local AI service."""
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
        self.model = model or getattr(settings, 'OLLAMA_MODEL', 'llama3.2')
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """Generate text using Ollama."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": stream
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            
            if stream:
                # Handle streaming response
                full_response = ""
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        full_response += data.get("response", "")
                        if data.get("done"):
                            break
                return full_response
            else:
                data = response.json()
                return data.get("response", "")
                
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is installed and running."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")
    
    async def chat(
        self,
        messages: List[dict],
        temperature: float = 0.7
    ) -> str:
        """Chat completion using Ollama."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
            
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is installed and running."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama chat failed: {e}")
    
    async def pull_model(self, model: str = None) -> bool:
        """Pull a model from Ollama library."""
        model_name = model or self.model
        
        try:
            payload = {"name": model_name}
            response = await self.client.post("/api/pull", json=payload, timeout=300.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
    
    async def check_connection(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = await self.client.get("/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# NLP Service using Ollama
class LocalNLPService:
    """Local NLP service using Ollama."""
    
    def __init__(self):
        self.client = OllamaClient()
        
        # System prompts
        self.summarize_system = """You are a content summarizer for a college newsletter. 
Your task is to convert long articles into concise 2-3 minute summaries for busy students.

Format your response as:
- **Hook**: One catchy sentence that grabs attention
- **Why it matters**: One line explaining relevance
- **Key points**: 3-6 bullet points (one idea each)
- **Action step**: One practical takeaway

Keep it brief, engaging, and student-friendly. Use emojis where appropriate."""
        
        self.headline_system = """You are a headline writer for a college tech newsletter.
Create catchy, click-worthy headlines (max 10 words) that make students want to read more.

Rules:
- Use power words
- Create curiosity gaps
- Keep it under 10 words
- Make it relevant to students"""
    
    async def summarize_content(
        self,
        title: str,
        content: str,
        category: str = "tech"
    ) -> dict:
        """Summarize content for newsletter."""
        
        prompt = f"""Title: {title}
Category: {category}

Content:
{content[:3000]}  # Truncate for token limit

Please provide a 2-3 minute summary in the specified format."""
        
        response = await self.client.generate(
            prompt=prompt,
            system=self.summarize_system,
            temperature=0.7
        )
        
        # Parse response into structured format
        return self._parse_summary(response)
    
    async def generate_headline(self, title: str, content: str) -> str:
        """Generate catchy headline."""
        
        prompt = f"""Original title: {title}

Content preview:
{content[:500]}

Create 3 catchy headlines and return only the best one:"""
        
        headline = await self.client.generate(
            prompt=prompt,
            system=self.headline_system,
            temperature=0.8
        )
        
        return headline.strip().strip('"').strip("'")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding using local model."""
        # Ollama doesn't have built-in embeddings, we'll use a workaround
        # or return empty list for now (implement with sentence-transformers)
        return []
    
    def _parse_summary(self, text: str) -> dict:
        """Parse summary text into structured format."""
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
            
            if 'hook' in lower or line.startswith('**'):
                current_section = 'hook'
                result['hook'] = line.replace('**', '').replace('Hook:', '').strip()
            elif 'why it matters' in lower or 'relevance' in lower:
                current_section = 'why'
                result['why_it_matters'] = line.replace('**', '').replace('Why it matters:', '').strip()
            elif 'key point' in lower or 'bullet' in lower or line.startswith('-'):
                current_section = 'points'
                if line.startswith('-') or line.startswith('•'):
                    result['key_points'].append(line.lstrip('- •').strip())
            elif 'action' in lower or 'takeaway' in lower:
                current_section = 'action'
                result['action_step'] = line.replace('**', '').replace('Action step:', '').strip()
            else:
                # Continue previous section
                if current_section == 'hook' and not result['hook']:
                    result['hook'] = line
                elif current_section == 'why' and not result['why_it_matters']:
                    result['why_it_matters'] = line
                elif current_section == 'points':
                    result['key_points'].append(line)
                elif current_section == 'action' and not result['action_step']:
                    result['action_step'] = line
        
        return result


async def check_ollama_status() -> dict:
    """Check Ollama installation status."""
    client = OllamaClient()
    
    try:
        is_running = await client.check_connection()
        
        if not is_running:
            return {
                "status": "not_running",
                "message": "Ollama is not running. Please start it first.",
                "install_url": "https://ollama.com/download"
            }
        
        models = await client.list_models()
        target_model = client.model
        
        if target_model not in models:
            return {
                "status": "model_missing",
                "message": f"Model '{target_model}' not found. Pull it with: ollama pull {target_model}",
                "models_available": models
            }
        
        return {
            "status": "ready",
            "message": f"Ollama is ready with model: {target_model}",
            "models_available": models
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        await client.close()
