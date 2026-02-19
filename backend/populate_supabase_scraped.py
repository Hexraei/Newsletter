"""Populate Supabase scraped_items table from latest scraper JSON."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx

from app.config import settings


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _latest_scraped_file() -> Path | None:
    data_dir = _repo_root() / "scraper_platform" / "data"
    files = sorted(data_dir.glob("scraped_*.json"), reverse=True)
    return files[0] if files else None


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _load_items() -> list[dict]:
    latest = _latest_scraped_file()
    if not latest or not latest.exists():
        return []

    payload = json.loads(latest.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if not isinstance(items, list):
        return []

    cleaned: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cleaned.append(
            {
                "source": item.get("source"),
                "source_type": item.get("source_type"),
                "title": item.get("title") or "",
                "url": item.get("url"),
                "content": item.get("content"),
                "author": item.get("author"),
                "published_at": item.get("published_at"),
                "scraped_at": item.get("scraped_at"),
                "engagement": _parse_json_field(item.get("engagement")),
                "metadata": _parse_json_field(item.get("metadata")),
                "content_hash": item.get("content_hash"),
                "category": item.get("category"),
            }
        )
    return cleaned


async def _populate() -> None:
    base_url = (settings.SUPABASE_URL or "").rstrip("/")
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY
    table = settings.SUPABASE_SCRAPED_TABLE
    if not base_url or not service_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env")

    items = _load_items()
    if not items:
        raise RuntimeError("No scraped items found in scraper_platform/data")

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        del_resp = await client.delete(f"{base_url}/rest/v1/{table}?id=gt.0", headers=headers)
        if del_resp.status_code >= 400:
            raise RuntimeError(f"Failed to clear {table}: {del_resp.status_code} {del_resp.text}")

        batch_size = 100
        inserted = 0
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            resp = await client.post(f"{base_url}/rest/v1/{table}", headers=headers, json=batch)
            if resp.status_code >= 400:
                raise RuntimeError(f"Insert failed at batch {i // batch_size + 1}: {resp.status_code} {resp.text}")
            inserted += len(batch)

        count_headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Range": "0-0",
            "Prefer": "count=exact",
        }
        count_resp = await client.get(f"{base_url}/rest/v1/{table}?select=id", headers=count_headers)
        total = count_resp.headers.get("content-range", "*/0").split("/")[-1]

    print(f"Inserted: {inserted}")
    print(f"Supabase {table} row count: {total}")


if __name__ == "__main__":
    asyncio.run(_populate())
