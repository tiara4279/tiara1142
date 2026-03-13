"""Data source layer with resilient fallbacks."""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional

import requests

from config import AppConfig
from utils import to_float

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def fetch_fred_latest(
    series_id: str,
    config: AppConfig,
    previous_points: int = 2,
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

    params = {
        "series_id": series_id,
        "api_key": config.fred_api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": max(previous_points + 2, 20),
        "observation_end": date.today().isoformat(),
    }

    try:
        r = requests.get(FRED_BASE, params=params, timeout=config.request_timeout)
        r.raise_for_status()
        data = r.json()
        observations = data.get("observations", [])

        valid = []
        for obs in observations:
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
                "error": "No valid observations",
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
    """Optional source for Fear & Greed index.

    This endpoint can be unstable / unavailable depending on environment.
    """
    # Public endpoint sometimes reachable; if unavailable we safely return N/A.
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        score = to_float(data.get("fear_and_greed", {}).get("score"))
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
