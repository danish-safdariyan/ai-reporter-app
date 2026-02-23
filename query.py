"""
World Bank Indicators API (V2) query logic.
From LAB_your_good_api_query / LAB_cursor_shiny_app.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

_query_cache: Dict[Tuple[str, ...], pd.DataFrame] = {}

BASE_URL = "https://api.worldbank.org/v2"
ENV_API_KEY = "WORLD_BANK_API_KEY"


def get_api_key_status() -> Tuple[bool, str]:
    """Check if API key is set. Returns (is_set, message)."""
    key = os.getenv(ENV_API_KEY)
    if key:
        return True, f"{ENV_API_KEY} is set."
    return False, (
        f"Warning: {ENV_API_KEY} is not set. "
        "The World Bank API often works without a key; you can still run the query."
    )


def build_url(
    countries: List[str],
    indicator: str,
    start_year: int,
    end_year: int,
    per_page: int = 20000,
    page: int = 1,
) -> str:
    """Build World Bank API URL for country/indicator endpoint."""
    countries_str = ";".join(c.strip().upper() for c in countries if c and c.strip())
    date_range = f"{start_year}:{end_year}"
    url = (
        f"{BASE_URL}/country/{countries_str}/indicator/{indicator}"
        f"?date={date_range}&format=json&per_page={per_page}&page={page}"
    )
    return url


def fetch_json(url: str, timeout: int = 30) -> List[Any]:
    """GET URL and return parsed JSON. Raises on HTTP or JSON errors."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError("API response is not a list.")
    return data


def normalize_records(payload: List[Any]) -> pd.DataFrame:
    """Convert World Bank response [metadata, records] to a DataFrame."""
    if len(payload) < 2:
        raise RuntimeError("Unexpected response structure (expected [meta, records]).")
    records = payload[1]
    if not isinstance(records, list):
        raise RuntimeError("Unexpected records type (expected a list of dicts).")

    rows: List[Dict[str, Any]] = []
    for r in records:
        rows.append({
            "country_id": (r.get("country") or {}).get("id"),
            "country_name": (r.get("country") or {}).get("value"),
            "indicator_id": (r.get("indicator") or {}).get("id"),
            "indicator_name": (r.get("indicator") or {}).get("value"),
            "year": r.get("date"),
            "value": r.get("value"),
        })
    df = pd.DataFrame(rows)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.sort_values(["country_name", "year"]).reset_index(drop=True)
    return df


def fetch_all_pages(
    countries: List[str],
    indicator: str,
    start_year: int,
    end_year: int,
    per_page: int,
) -> pd.DataFrame:
    """Fetch all pages of results and combine into one DataFrame."""
    all_dfs: List[pd.DataFrame] = []
    page = 1
    while True:
        url = build_url(
            countries=countries,
            indicator=indicator,
            start_year=start_year,
            end_year=end_year,
            per_page=per_page,
            page=page,
        )
        payload = fetch_json(url)
        if len(payload) < 2 or not payload[1]:
            break
        df = normalize_records(payload)
        all_dfs.append(df)
        if len(df) < per_page:
            break
        page += 1
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True).drop_duplicates().reset_index(drop=True)


def _cache_key(
    countries: List[str],
    indicator: str,
    start_year: int,
    end_year: int,
    per_page: int,
) -> Tuple[str, ...]:
    return (",".join(sorted(c.strip().upper() for c in countries if c)), indicator, str(start_year), str(end_year), str(per_page))


def run_query(
    countries: List[str],
    indicator: str,
    start_year: int,
    end_year: int,
    per_page: int = 20000,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Run the World Bank query with optional in-memory cache.
    Returns DataFrame; raises on validation or API errors.
    """
    if not countries or not any(c and c.strip() for c in countries):
        raise ValueError("At least one country must be selected.")
    if not indicator or not indicator.strip():
        raise ValueError("Indicator is required.")
    if start_year > end_year:
        raise ValueError("Start year must be less than or equal to end year.")

    key = _cache_key(countries, indicator, start_year, end_year, per_page)
    if use_cache and key in _query_cache:
        return _query_cache[key].copy()

    df = fetch_all_pages(
        countries=countries,
        indicator=indicator,
        start_year=start_year,
        end_year=end_year,
        per_page=per_page,
    )
    _query_cache[key] = df.copy()
    return df
