"""Shared utility helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd


def to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        if isinstance(value, str) and value.strip() in {"", ".", "nan", "NaN"}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_value(value: Optional[float], suffix: str = "", precision: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.{precision}f}{suffix}"


def now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def week_delta(latest: Optional[float], previous: Optional[float]) -> Optional[float]:
    if latest is None or previous is None:
        return None
    return latest - previous


def status_badge(status: str) -> str:
    mapping = {
        "안정": "🟢 안정",
        "주의": "🟠 주의",
        "위험": "🔴 위험",
        "N/A": "⚪ N/A",
    }
    return mapping.get(status, "⚪ N/A")
