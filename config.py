"""Configuration for the liquidity & risk dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    fred_api_key: Optional[str]
    request_timeout: int = 12


def get_config() -> AppConfig:
    return AppConfig(
        fred_api_key=os.getenv("FRED_API_KEY"),
    )


# NOTE:
# - IDs below are best-effort and may change by source maintenance.
# - Uncertain IDs are kept optional in app logic and can safely fail to N/A.
FRED_SERIES: Dict[str, str] = {
    "vix": "VIXCLS",  # CBOE Volatility Index: VIX
    "yield_curve_10y2y": "T10Y2Y",  # 10-Year Treasury Constant Maturity Minus 2-Year
    "fed_balance_sheet": "WALCL",  # Assets: Total Assets, Weekly Level
    "reserve_balances": "WRESBAL",  # Reserve balances at Federal Reserve Banks, weekly level
    "rrp": "RRPONTSYD",  # Overnight Reverse Repurchase Agreements: Treasury Securities Sold by the Fed
    "tga": "WTREGEN",  # U.S. Treasury General Account (commonly published in millions)
    "hy_spread": "BAMLH0A0HYM2",  # ICE BofA US High Yield Index Option-Adjusted Spread
    "financial_stress": "STLFSI4",  # St. Louis Fed Financial Stress Index
    "sofr": "SOFR",  # Secured Overnight Financing Rate
    "effr": "DFF",  # Effective Federal Funds Rate (daily)
    "iorb": "IORB",  # TODO: verify availability/definition in your FRED tenant if request fails
    "mmf_total_assets": "MMMFFAQ027S",  # TODO: confirm preferred MMF total assets series for your workflow
}
