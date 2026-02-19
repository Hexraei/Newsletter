"""Lightweight Supabase REST integration for feed source/cache."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings


def _parse_datetime(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    raw = value.strip().replace("Z", "+00:00")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except Exception:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


class SupabaseLiteClient:
    """Tiny wrapper around PostgREST endpoints for lite mode."""

    def __init__(self) -> None:
        self.supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
        self.read_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        self.write_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.scraped_table = settings.SUPABASE_SCRAPED_TABLE
        self.cache_table = settings.SUPABASE_RANKED_CACHE_TABLE
        self.cache_key = settings.SUPABASE_CACHE_KEY
        self.cache_ttl_minutes = max(1, settings.SUPABASE_CACHE_TTL_MINUTES)
        self.fetch_limit = max(20, min(settings.SUPABASE_FETCH_LIMIT, 1000))

    @property
    def enabled(self) -> bool:
        return bool(self.supabase_url and self.read_key)

    @property
    def can_write(self) -> bool:
        return bool(self.supabase_url and self.write_key)

    def _headers(self, key: str) -> dict[str, str]:
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    async def fetch_scraped_items(self, limit: int | None = None) -> list[dict]:
        if not self.enabled:
            return []

        query_limit = max(20, min(limit or self.fetch_limit, 1000))
        url = (
            f"{self.supabase_url}/rest/v1/{self.scraped_table}"
            f"?select=*"
            f"&order=published_at.desc.nullslast"
            f"&limit={query_limit}"
        )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url, headers=self._headers(self.read_key))
                if response.status_code >= 400:
                    return []
                payload = response.json()
        except Exception:
            return []

        if not isinstance(payload, list):
            return []

        normalized: list[dict] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            row_copy = dict(row)
            row_copy["engagement"] = _parse_json_field(row_copy.get("engagement"))
            row_copy["metadata"] = _parse_json_field(row_copy.get("metadata"))
            normalized.append(row_copy)
        return normalized

    async def fetch_ranked_cache(self) -> dict | None:
        if not self.enabled:
            return None

        encoded_key = quote(self.cache_key, safe="")
        url = (
            f"{self.supabase_url}/rest/v1/{self.cache_table}"
            f"?select=cache_key,generated_at,payload"
            f"&cache_key=eq.{encoded_key}"
            f"&limit=1"
        )

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.get(url, headers=self._headers(self.read_key))
                if response.status_code >= 400:
                    return None
                payload = response.json()
        except Exception:
            return None

        if not isinstance(payload, list) or not payload:
            return None
        record = payload[0]
        if not isinstance(record, dict):
            return None

        generated_at = _parse_datetime(record.get("generated_at"))
        if generated_at is None:
            return None

        age = datetime.now(timezone.utc) - generated_at
        if age > timedelta(minutes=self.cache_ttl_minutes):
            return None

        data = _parse_json_field(record.get("payload"))
        return data if isinstance(data, dict) else None

    async def upsert_ranked_cache(self, payload: dict[str, Any]) -> bool:
        if not self.can_write:
            return False

        url = f"{self.supabase_url}/rest/v1/{self.cache_table}?on_conflict=cache_key"
        row = {
            "cache_key": self.cache_key,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        headers = self._headers(self.write_key)
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.post(url, headers=headers, json=[row])
                return response.status_code < 400
        except Exception:
            return False
