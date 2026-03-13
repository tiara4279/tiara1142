"""Data source layer with resilient fallbacks."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import requests

from config import AppConfig
from utils import to_float

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def _parse_obs_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def fetch_fred_latest(
    series_id: str,
    config: AppConfig,
    previous_points: int = 2,
    max_age_days: Optional[int] = None,
) -> Dict[str, Optional[float]]:
    """Fetch latest available value (+ previous values) from FRED.

    Returns a dict with keys: latest, previous, date, ok, error.
    """
    if not config.fred_api_key:
        return {
            "latest": None,
            "previous": None,
            "date": None,
            "ok": False,
            "error": "FRED_API_KEY not configured",
        }

    today = date.today()
    params = {
        "series_id": series_id,
        "api_key": config.fred_api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": max(previous_points + 2, 40),
        "observation_end": today.isoformat(),
    }
    if max_age_days is not None:
        params["observation_start"] = (today - timedelta(days=max_age_days * 4)).isoformat()

    try:
        r = requests.get(FRED_BASE, params=params, timeout=config.request_timeout)
        r.raise_for_status()
        data = r.json()
        observations = data.get("observations", [])

        valid = []
        for obs in observations:
            d = _parse_obs_date(obs.get("date"))
            if max_age_days is not None and d is not None and (today - d).days > max_age_days:
                continue
            v = to_float(obs.get("value"))
            if v is not None:
                valid.append({"date": obs.get("date"), "value": v})
            if len(valid) >= previous_points:
                break

        if not valid:
            return {
                "latest": None,
                "previous": None,
                "date": None,
                "ok": False,
                "error": "No valid observations in freshness window",
            }

        latest = valid[0]["value"]
        previous = valid[1]["value"] if len(valid) > 1 else None
        return {
            "latest": latest,
            "previous": previous,
            "date": valid[0]["date"],
            "ok": True,
            "error": None,
        }
    except Exception as e:  # noqa: BLE001 - keep app alive on any source failure
        return {
            "latest": None,
            "previous": None,
            "date": None,
            "ok": False,
            "error": str(e),
        }


def fetch_fear_greed_optional(timeout: int = 8) -> Dict[str, Optional[float]]:
    """Optional source for Fear & Greed index."""
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        score = to_float(data.get("fear_and_greed", {}).get("score"))
        # This source frequently omits stable date metadata.
        return {
            "latest": score,
            "previous": None,
            "date": None,
            "ok": score is not None,
            "error": None if score is not None else "score missing",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "latest": None,
            "previous": None,
            "date": None,
            "ok": False,
            "error": f"optional source unavailable: {e}",
        }


def fetch_fred_first_available(
    series_ids: List[str],
    config: AppConfig,
    previous_points: int = 2,
    max_age_days: Optional[int] = None,
) -> Dict[str, Optional[float]]:
    """Try multiple series IDs and return the first fresh, valid one.

    Only returns a series that satisfies freshness constraints.
    """
    last_error: Optional[str] = None
    for sid in series_ids:
        result = fetch_fred_latest(
            series_id=sid,
            config=config,
            previous_points=previous_points,
            max_age_days=max_age_days,
        )
        if result.get("ok"):
            result["series_id"] = sid
            return result
        last_error = result.get("error") or f"no data for {sid}"

    return {
        "latest": None,
        "previous": None,
        "date": None,
        "ok": False,
        "error": last_error or "No valid series candidates",
        "series_id": None,
    }
