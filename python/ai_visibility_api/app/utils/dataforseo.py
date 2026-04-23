import base64
import os
from dataclasses import dataclass

import requests


class DataForSeoError(Exception):
    pass


@dataclass(frozen=True)
class KeywordMetrics:
    search_volume: int
    difficulty: int  # 0–100


def _auth_header(login: str, password: str) -> str:
    token = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"


def fetch_keyword_metrics(query_text: str, *, location_code: int, language_code: str) -> KeywordMetrics:
    """
    Uses DataForSEO Keywords Data API (Google Ads search volume).
    Endpoint: /v3/keywords_data/google_ads/search_volume/live
    """
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        raise DataForSeoError("Missing DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD env vars")

    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
    headers = {
        "Authorization": _auth_header(login, password),
        "Content-Type": "application/json",
    }
    payload = [
        {
            "location_code": int(location_code),
            "language_code": language_code,
            "keywords": [query_text],
        }
    ]
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code >= 400:
        raise DataForSeoError(f"DataForSEO error {r.status_code}: {r.text[:500]}")
    data = r.json()
    tasks = (data or {}).get("tasks") or []
    result_items = (((tasks[0] or {}).get("result") or [{}])[0].get("items") or []) if tasks else []
    if not result_items:
        # No data returned; treat as 0 volume and unknown difficulty
        return KeywordMetrics(search_volume=0, difficulty=50)
    item = result_items[0] or {}
    volume = int(item.get("search_volume") or 0)

    # DataForSEO keywords_data response doesn't always include a consistent "difficulty" field.
    # We derive a proxy difficulty from competition (low/medium/high) and cpc when available.
    comp = (item.get("competition") or "").lower()
    if comp == "low":
        difficulty = 30
    elif comp == "medium":
        difficulty = 55
    elif comp == "high":
        difficulty = 75
    else:
        difficulty = 50
    return KeywordMetrics(search_volume=volume, difficulty=difficulty)

