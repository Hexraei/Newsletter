"""Google Gemini integration with structured output parsing."""

import json
import re
from typing import Any, Optional

import httpx

from app.config import settings


class GeminiService:
    """Gemini API service using REST endpoint via httpx."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    FALLBACK_MODELS = (
        "gemini-3.1-flash-lite-preview",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
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
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)
        self.model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        self.client = httpx.AsyncClient(timeout=30.0)
        self._unavailable_models: set[str] = set()

    def _model_candidates(self) -> list[str]:
        candidates: list[str] = []
        for m in [self.model] + list(self.FALLBACK_MODELS):
            if m not in self._unavailable_models and m not in candidates:
                candidates.append(m)
        return candidates or list(self.FALLBACK_MODELS)

    def _url(self, model: str, action: str = "generateContent") -> str:
        return f"{self.BASE_URL}/models/{model}:{action}?key={self.api_key}"

    async def _generate(
        self,
        prompt: str,
        *,
        system_instruction: str = "",
        temperature: float = 0.35,
        max_tokens: int = 500,
    ) -> str:
        """Call Gemini generateContent with model fallback on 429/5xx."""
        body: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        last_error = None
        for model in self._model_candidates():
            try:
                response = await self.client.post(self._url(model), json=body)

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        continue
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return parts[0].get("text", "") if parts else ""

                if response.status_code == 429:
                    self._unavailable_models.add(model)
                    last_error = f"429 quota exceeded for {model}"
                    continue

                if response.status_code >= 500:
                    last_error = f"{response.status_code} server error for {model}"
                    continue

                response.raise_for_status()
            except httpx.HTTPStatusError:
                raise
            except Exception as e:
                last_error = str(e)
                continue

        raise RuntimeError(f"All Gemini models failed: {last_error}")

    # ── Summarize ────────────────────────────────────────────────

    async def summarize_content(self, title: str, content: str, category: str = "tech") -> dict:
        """Summarize an article for college students."""
        context_terms = self._extract_context_terms(title, content, category)
        context_hint = ", ".join(context_terms[:10]) if context_terms else category

        system = """You are summarizing a news article for college students.

Extract the core information from the article. Do not invent or assume anything not stated in the text.

Return ONLY valid JSON (no markdown fences, no extra text):
{
  "what_happened": "1-2 plain sentences stating the main event. Include who, what, when if available.",
  "why_it_matters": "1-2 sentences on concrete impact — on jobs, technology, industry, or academics. Be specific.",
  "key_facts": ["3-5 specific facts from the article: numbers, names, dates, companies, technologies. Only facts explicitly stated."]
}

Rules:
- No markdown code fences. Return raw JSON only.
- Keep every statement grounded in the provided title/content.
- Never use filler phrases like 'stay informed' or 'this is important'.
- Include concrete terms from the source when possible."""

        user = (
            f"Title: {title}\n"
            f"Category: {category}\n\n"
            f"Content:\n{content[:3000]}\n\n"
            f"Key terms from source: {context_hint}\n\n"
            "Extract the core information as JSON."
        )

        text = await self._generate(user, system_instruction=system, temperature=0.35, max_tokens=500)
        summary = self._parse_summary(text)

        if self._is_summary_strong(summary, context_terms):
            return summary

        # One repair pass
        repair_prompt = (
            f"Title: {title}\nCategory: {category}\nContext terms: {context_hint}\n\n"
            f"Original content:\n{content[:3000]}\n\n"
            f"Weak summary JSON:\n{json.dumps(summary, ensure_ascii=True)}\n\n"
            "Return improved JSON only."
        )
        repair_system = """You are revising a weak article summary. Keep the same JSON schema exactly.

Fix these problems:
- Remove generic language and filler phrases.
- Ground every statement in specific facts from the source text.
- Ensure key_facts contains actual data points (numbers, names, dates, technologies).
- Do not add information that isn't in the original article.
- Return raw JSON only, no markdown fences."""

        repaired_text = await self._generate(
            repair_prompt, system_instruction=repair_system, temperature=0.3, max_tokens=520
        )
        repaired = self._parse_summary(repaired_text)
        if self._is_summary_strong(repaired, context_terms):
            return repaired

        return self._contextual_fallback_summary(title, content, category, context_terms)

    # ── Headlines ────────────────────────────────────────────────

    async def generate_headline(self, title: str, content: str) -> str:
        system = "Create concise headlines for a CS college newsletter (max 10 words)."
        prompt = (
            f"Original: {title}\n"
            f"Content: {content[:500]}\n\n"
            "Return only headline text."
        )
        headline = await self._generate(prompt, system_instruction=system, temperature=0.6, max_tokens=50)
        return headline.strip().strip('"').strip("'")

    async def generate_breaking_headline(self, title: str, content: str, source: str = "") -> str:
        system = """You are a breaking news headline writer for a college tech newsletter.

Rules:
- Max 8 words
- Use active, urgent language without clickbait
- Keep it factual and specific
- Return only headline text"""

        prompt = (
            f"Source: {source or 'Tech Source'}\n"
            f"Original title: {title}\n"
            f"Content summary: {content[:800]}\n\n"
            "Return one breaking headline."
        )
        headline = await self._generate(prompt, system_instruction=system, temperature=0.55, max_tokens=30)
        headline = headline.strip().strip('"').strip("'")
        words = headline.split()
        if len(words) > 10:
            headline = " ".join(words[:8]) + "..."
        return headline

    # ── Parsing helpers (same patterns as GroqService) ───────────

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
            candidates.append(raw[start: end + 1])

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
            "hook": self._clean_line(payload.get("what_happened") or payload.get("hook")),
            "why_it_matters": self._clean_line(payload.get("why_it_matters") or payload.get("why")),
            "key_points": [],
            "action_step": self._clean_line(payload.get("action_step") or payload.get("next_step") or ""),
        }

        raw_points = payload.get("key_facts") or payload.get("key_points")
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
        points = [self._clean_line(p, max_len=200) for p in (summary.get("key_points") or [])]
        points = [p for p in points if p]

        if self._word_count(hook) < 6:
            return False
        if self._word_count(why) < 6:
            return False
        if len(points) < 2:
            return False

        merged = " ".join([hook, why, *points]).lower()
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
        self, title: str, content: str, category: str, context_terms: list[str]
    ) -> dict:
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
        parsed_json = self._extract_json_object(text)
        if parsed_json:
            normalized = self._normalize_summary(parsed_json)
            if (
                normalized["hook"]
                and normalized["why_it_matters"]
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
            if "hook" in lower or "summary" in lower or "happened" in lower:
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
        await self.client.aclose()


async def check_gemini_status(api_key: str, model: str = "gemini-3.1-flash-lite-preview") -> dict:
    """Check Gemini API status by listing models."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}?key={api_key}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "ready",
                    "provider": "Gemini",
                    "model": data.get("name", model),
                    "message": "Gemini API is configured and working",
                }

            return {
                "status": "error",
                "provider": "Gemini",
                "message": f"Gemini API error: {response.status_code} — {response.text[:200]}",
            }
    except Exception as e:
        return {
            "status": "error",
            "provider": "Gemini",
            "message": str(e),
        }
