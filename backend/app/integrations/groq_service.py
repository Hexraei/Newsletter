"""Groq integration with robust model fallback and structured parsing."""

import json
import re
from typing import Any, Optional

import httpx

from app.config import settings


class GroqService:
    """Groq API service with resilient model fallback and structured output parsing."""

    FALLBACK_MODELS = (
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "gemma2-9b-it",
    )

    GENERIC_PHRASES = (
        "stay informed",
        "this is important",
        "could impact",
        "in today's world",
        "for students",
        "rapidly evolving",
        "ever-changing landscape",
        "game changer",
        "key takeaway",
    )

    STOPWORDS = {
        "the", "and", "for", "with", "that", "this", "from", "into", "your", "about",
        "have", "will", "they", "them", "their", "there", "would", "could", "should",
        "after", "before", "while", "where", "when", "what", "which", "than", "then",
        "just", "more", "most", "over", "under", "using", "used", "like", "also",
        "news", "story", "article", "today", "latest", "update", "tech", "student",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GROQ_API_KEY", None)
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self.model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
        self._unavailable_models: set[str] = set()

    def _model_candidates(self, *, prefer_fallback: bool = False) -> list[str]:
        ordered = list(self.FALLBACK_MODELS) + [self.model] if prefer_fallback else [self.model] + list(self.FALLBACK_MODELS)
        candidates: list[str] = []
        for model in ordered:
            if model in self._unavailable_models:
                continue
            if model not in candidates:
                candidates.append(model)

        if not candidates:
            # Emergency fallback if everything was marked unavailable in this process.
            candidates = list(self.FALLBACK_MODELS)
        return candidates

    @staticmethod
    def _is_retryable_model_error(payload: dict) -> bool:
        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return False

        code = str(error.get("code") or "").lower()
        msg = str(error.get("message") or "").lower()
        retry_signals = (
            "model_decommissioned",
            "decommissioned",
            "no longer supported",
            "does not exist",
            "not found",
            "not available",
        )
        return any(signal in code or signal in msg for signal in retry_signals)

    async def _chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        prefer_fallback: bool = False,
    ) -> tuple[dict, str]:
        """Run chat completion with automatic model fallback."""
        last_payload: dict | None = None

        for model_name in self._model_candidates(prefer_fallback=prefer_fallback):
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )

            try:
                payload = response.json()
            except Exception:
                payload = {}

            if response.status_code == 200:
                return payload, model_name

            last_payload = payload
            if response.status_code in (400, 404) and self._is_retryable_model_error(payload):
                self._unavailable_models.add(model_name)
                continue

            response.raise_for_status()

        err_msg = "All Groq model attempts failed"
        if isinstance(last_payload, dict):
            error = last_payload.get("error") or {}
            if isinstance(error, dict) and error.get("message"):
                err_msg = str(error["message"])
        raise RuntimeError(err_msg)

    async def summarize_content(self, title: str, content: str, category: str = "tech") -> dict:
        """Summarize content using JSON-first prompts for better relevance."""

        context_terms = self._extract_context_terms(title, content, category)
        context_hint = ", ".join(context_terms[:10]) if context_terms else category

        system_prompt = """You are a senior editor for a computer science college newsletter.

Your job is to interpret news intelligently, not just shorten text.
Focus on relevance for CS students: architecture trade-offs, performance, security, tooling, hiring signals, and project decisions.
Write with technical clarity and creative framing, but never fluff.

Return ONLY valid JSON with this exact schema:
{
  "hook": "one vivid sentence under 24 words",
  "why_it_matters": "one concrete sentence under 32 words",
  "key_points": ["3 to 5 concise factual bullets"],
  "action_step": "one practical next step for students under 28 words"
}

Rules:
- No markdown, no code fences, no extra keys.
- Keep every field grounded in the provided title/content.
- Avoid generic filler like "stay informed" or "this is important".
- Mention concrete technical or career implications.
- Include at least two context-specific terms from the source when possible."""

        user_prompt = (
            f"Title: {title}\n"
            f"Category: {category}\n\n"
            f"Content:\n{content[:3000]}\n\n"
            f"Context terms to anchor: {context_hint}\n\n"
            "Generate the JSON now."
        )

        data, _model_used = await self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
            max_tokens=500,
            prefer_fallback=True,
        )

        summary_text = data["choices"][0]["message"]["content"]
        summary = self._parse_summary(summary_text)
        if self._is_summary_strong(summary, context_terms):
            return summary

        repair_system = """You are revising a weak summary. Keep the same JSON schema exactly.

Fix these problems:
- Remove generic language and filler.
- Make statements technically specific and grounded in the source.
- Keep the tone creative but factual.
- Ensure each key point adds new information, not repetition.
- Include concrete implications for students building projects or preparing for interviews."""

        repair_prompt = (
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"Context terms: {context_hint}\n\n"
            f"Original content:\n{content[:3000]}\n\n"
            f"Weak summary JSON:\n{json.dumps(summary, ensure_ascii=True)}\n\n"
            "Return improved JSON only."
        )

        repaired_data, _model_used = await self._chat_completion(
            messages=[
                {"role": "system", "content": repair_system},
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0.3,
            max_tokens=520,
            prefer_fallback=True,
        )

        repaired_text = repaired_data["choices"][0]["message"]["content"]
        repaired_summary = self._parse_summary(repaired_text)
        if self._is_summary_strong(repaired_summary, context_terms):
            return repaired_summary

        return self._contextual_fallback_summary(title, content, category, context_terms)

    async def generate_headline(self, title: str, content: str) -> str:
        """Generate concise headline."""
        system_prompt = "Create concise headlines for a CS college newsletter (max 10 words)."
        user_prompt = (
            f"Original: {title}\n"
            f"Content: {content[:500]}\n\n"
            "Return only headline text."
        )

        data, _model_used = await self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=50,
        )

        headline = data["choices"][0]["message"]["content"].strip()
        return headline.strip('"').strip("'")

    async def generate_breaking_headline(self, title: str, content: str, source: str = "") -> str:
        """Generate urgent, factual breaking news headline."""
        system_prompt = """You are a breaking news headline writer for a college tech newsletter.

Rules:
- Max 8 words
- Use active, urgent language without clickbait
- Keep it factual and specific
- Return only headline text"""

        user_prompt = (
            f"Source: {source or 'Tech Source'}\n"
            f"Original title: {title}\n"
            f"Content summary: {content[:800]}\n\n"
            "Return one breaking headline."
        )

        data, _model_used = await self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.55,
            max_tokens=30,
        )

        headline = data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        words = headline.split()
        if len(words) > 10:
            headline = " ".join(words[:8]) + "..."
        return headline

    @staticmethod
    def _clean_line(value: Any, max_len: int = 240) -> str:
        text = str(value or "").replace("\n", " ").strip()
        text = re.sub(r"\s+", " ", text)
        text = text.strip(" -*•\t")
        if len(text) > max_len:
            text = text[: max_len - 3].rstrip() + "..."
        return text

    @staticmethod
    def _extract_json_object(text: str) -> dict | None:
        raw = text.strip()
        candidates = [raw]

        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1))

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
            "hook": self._clean_line(payload.get("hook")),
            "why_it_matters": self._clean_line(payload.get("why_it_matters") or payload.get("why")),
            "key_points": [],
            "action_step": self._clean_line(payload.get("action_step") or payload.get("next_step")),
        }

        raw_points = payload.get("key_points")
        points: list[str] = []
        if isinstance(raw_points, list):
            points = [self._clean_line(point, max_len=160) for point in raw_points]
        elif isinstance(raw_points, str):
            points = [self._clean_line(part, max_len=160) for part in re.split(r"[\n;•-]+", raw_points)]

        result["key_points"] = [point for point in points if len(point) >= 10][:5]
        return result

    @staticmethod
    def _word_count(text: str) -> int:
        return len([w for w in str(text).strip().split() if w])

    def _extract_context_terms(self, title: str, content: str, category: str) -> list[str]:
        corpus = f"{title} {category} {content[:2000]}"
        raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9+#\-.]{2,}", corpus)
        seen: set[str] = set()
        terms: list[str] = []
        for term in raw_terms:
            low = term.lower()
            if low in self.STOPWORDS or low.isdigit():
                continue
            if len(low) < 4:
                continue
            if low in seen:
                continue
            seen.add(low)
            terms.append(term)
            if len(terms) >= 24:
                break
        return terms

    def _is_summary_strong(self, summary: dict, context_terms: list[str]) -> bool:
        hook = self._clean_line(summary.get("hook"))
        why = self._clean_line(summary.get("why_it_matters"))
        action = self._clean_line(summary.get("action_step"))
        points = [self._clean_line(p, max_len=200) for p in (summary.get("key_points") or [])]
        points = [p for p in points if p]

        if self._word_count(hook) < 8:
            return False
        if self._word_count(why) < 10:
            return False
        if self._word_count(action) < 10:
            return False
        if len(points) < 3:
            return False
        if any(self._word_count(p) < 8 for p in points[:3]):
            return False

        merged = " ".join([hook, why, action, *points]).lower()
        generic_hits = sum(1 for phrase in self.GENERIC_PHRASES if phrase in merged)
        if generic_hits >= 2:
            return False

        if context_terms:
            low_terms = [t.lower() for t in context_terms[:10]]
            hit_count = sum(1 for t in low_terms if t in merged)
            if hit_count < 2:
                return False

        return True

    def _contextual_fallback_summary(
        self,
        title: str,
        content: str,
        category: str,
        context_terms: list[str],
    ) -> dict:
        """Last-resort summary that is still contextual instead of generic."""
        sentences = [
            self._clean_line(s, max_len=220)
            for s in re.split(r"(?<=[.!?])\s+", content)
            if self._word_count(s) >= 8
        ]

        key_points: list[str] = []
        for sentence in sentences:
            low = sentence.lower()
            if context_terms and not any(term.lower() in low for term in context_terms[:10]):
                continue
            if sentence not in key_points:
                key_points.append(sentence)
            if len(key_points) >= 3:
                break

        while len(key_points) < 3 and sentences:
            candidate = sentences[len(key_points) % len(sentences)]
            if candidate not in key_points:
                key_points.append(candidate)

        keyword_a = context_terms[0] if context_terms else category
        keyword_b = context_terms[1] if len(context_terms) > 1 else "engineering"

        hook = self._clean_line(
            f"{title}: the core shift is in {keyword_a}, and it changes how students should approach {keyword_b} decisions this semester.",
            max_len=220,
        )
        why = self._clean_line(
            f"This matters because teams interviewing new grads now ask for practical reasoning about {keyword_a} trade-offs, not just definitions.",
            max_len=220,
        )
        action = self._clean_line(
            f"Build a mini project that applies {keyword_a}, document trade-offs, and prepare one interview-ready explanation of your technical choices.",
            max_len=220,
        )

        return {
            "hook": hook,
            "why_it_matters": why,
            "key_points": key_points[:5],
            "action_step": action,
        }

    def _parse_summary(self, text: str) -> dict:
        """Parse summary text (JSON-first, then line fallback)."""
        parsed_json = self._extract_json_object(text)
        if parsed_json:
            normalized = self._normalize_summary(parsed_json)
            if (
                normalized["hook"]
                and normalized["why_it_matters"]
                and normalized["action_step"]
                and normalized["key_points"]
            ):
                return normalized

        result = {
            "hook": "",
            "why_it_matters": "",
            "key_points": [],
            "action_step": "",
        }

        for raw_line in text.strip().split("\n"):
            line = self._clean_line(raw_line)
            if not line:
                continue

            lower = line.lower()
            if "hook" in lower or "summary" in lower:
                result["hook"] = self._clean_line(line.split(":", 1)[-1])
            elif "why" in lower and "matter" in lower:
                result["why_it_matters"] = self._clean_line(line.split(":", 1)[-1])
            elif "action" in lower or "takeaway" in lower or "step" in lower:
                result["action_step"] = self._clean_line(line.split(":", 1)[-1])
            elif line.startswith("-") or line.startswith("•"):
                point = self._clean_line(line.lstrip("- •"), max_len=160)
                if point and len(point) >= 10:
                    result["key_points"].append(point)

        if not result["hook"]:
            result["hook"] = "Key update students should notice now"
        if not result["why_it_matters"]:
            result["why_it_matters"] = "This can influence what you build, learn, and discuss in interviews this semester"
        if not result["key_points"]:
            result["key_points"] = [
                "The story signals a relevant technical or industry shift",
                "Students can use this context for projects and interview preparation",
                "Expect follow-on changes in tools, workflows, or hiring priorities",
            ]
        if not result["action_step"]:
            result["action_step"] = "Translate this trend into one practical project, skill, or discussion topic this week"

        return result

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def check_groq_status(api_key: str) -> dict:
    """Check Groq API status and validate configured model availability."""
    configured_model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
    try:
        client = httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"})
        response = await client.get("https://api.groq.com/openai/v1/models")
        await client.aclose()

        if response.status_code != 200:
            return {
                "status": "error",
                "provider": "Groq",
                "message": f"Groq API error: {response.status_code}",
            }

        payload = response.json()
        models = payload.get("data") if isinstance(payload, dict) else []
        model_ids = {
            item.get("id")
            for item in models
            if isinstance(item, dict) and item.get("id")
        }

        if configured_model in model_ids:
            return {
                "status": "ready",
                "provider": "Groq",
                "model": configured_model,
                "message": "Groq API is configured and working",
            }

        suggested_model = None
        for candidate in GroqService.FALLBACK_MODELS:
            if candidate in model_ids:
                suggested_model = candidate
                break

        return {
            "status": "degraded",
            "provider": "Groq",
            "model": configured_model,
            "fallback_model": suggested_model,
            "message": "Configured Groq model is unavailable; fallback model should be used",
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": "Groq",
            "message": str(e),
        }
