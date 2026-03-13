"""Indicator computation and risk classification rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from config import AppConfig, FRED_SERIES
from data_sources import fetch_fear_greed_optional, fetch_fred_latest
from utils import fmt_value, week_delta


@dataclass
class IndicatorRow:
    name: str
    value: Optional[float]
    display_value: str
    status: str
    frequency: str
    source: str
    latest_date: Optional[str]
    note: str = ""


def classify(name: str, value: Optional[float]) -> str:
    if value is None:
        return "N/A"

    if name == "VIX":
        return "안정" if value < 20 else "주의" if value <= 30 else "위험"
    if name == "장단기 금리차 (10Y-2Y)":
        return "위험" if value < 0 else "주의" if value <= 0.5 else "안정"
    if name == "하이일드 스프레드":
        return "안정" if value < 4 else "주의" if value <= 6 else "위험"
    if name == "금융스트레스지수":
        return "안정" if value < 0 else "주의" if value <= 1 else "위험"
    if "증감" in name:
        return "주의" if abs(value) > 100 else "안정"
    if name in {"SOFR/EFFR 스프레드", "SOFR/IORB 스프레드"}:
        return "안정" if abs(value) <= 0.1 else "주의" if abs(value) <= 0.25 else "위험"

    # Generic fallback thresholds for level-type liquidity indicators.
    return "안정"


def _row(
    name: str,
    value: Optional[float],
    frequency: str,
    source: str,
    latest_date: Optional[str],
    note: str = "",
    suffix: str = "",
    precision: int = 2,
) -> IndicatorRow:
    return IndicatorRow(
        name=name,
        value=value,
        display_value=fmt_value(value, suffix=suffix, precision=precision),
        status=classify(name, value),
        frequency=frequency,
        source=source,
        latest_date=latest_date,
        note=note,
    )


def build_indicators(config: AppConfig) -> List[IndicatorRow]:
    rows: List[IndicatorRow] = []

    vix = fetch_fred_latest(FRED_SERIES["vix"], config)
    yc = fetch_fred_latest(FRED_SERIES["yield_curve_10y2y"], config)
    walcl = fetch_fred_latest(FRED_SERIES["fed_balance_sheet"], config)
    reserves = fetch_fred_latest(FRED_SERIES["reserve_balances"], config)
    rrp = fetch_fred_latest(FRED_SERIES["rrp"], config)
    tga = fetch_fred_latest(FRED_SERIES["tga"], config)
    hy = fetch_fred_latest(FRED_SERIES["hy_spread"], config)
    stress = fetch_fred_latest(FRED_SERIES["financial_stress"], config)
    sofr = fetch_fred_latest(FRED_SERIES["sofr"], config)
    effr = fetch_fred_latest(FRED_SERIES["effr"], config)
    iorb = fetch_fred_latest(FRED_SERIES["iorb"], config)
    mmf = fetch_fred_latest(FRED_SERIES["mmf_total_assets"], config)
    fear = fetch_fear_greed_optional()

    rows.append(_row("VIX", vix["latest"], "일간", "FRED", vix["date"]))
    rows.append(_row("장단기 금리차 (10Y-2Y)", yc["latest"], "일간", "FRED", yc["date"], suffix="%"))
    rows.append(_row("연준 대차대조표", walcl["latest"], "주간", "FRED", walcl["date"], suffix="B"))
    rows.append(_row("지급준비금", reserves["latest"], "주간", "FRED", reserves["date"], suffix="B"))
    rows.append(_row("역레포(RRP)", rrp["latest"], "일간", "FRED", rrp["date"], suffix="B"))
    rows.append(_row("TGA", tga["latest"], "일간/주간", "FRED", tga["date"], suffix="B"))

    rows.append(_row("지급준비금 주간 증감", week_delta(reserves["latest"], reserves["previous"]), "주간", "FRED", reserves["date"], suffix="B"))
    rows.append(_row("TGA 주간 증감", week_delta(tga["latest"], tga["previous"]), "주간", "FRED", tga["date"], suffix="B"))

    rows.append(
        _row(
            "MMF 총 잔액",
            mmf["latest"],
            "저빈도(월/분기 가능)",
            "FRED(optional)",
            mmf["date"],
            note="데이터 주기가 낮거나 시리즈 정의가 변경될 수 있음",
            suffix="B",
        )
    )

    mmf_vs_rrp = None
    if mmf["latest"] is not None and rrp["latest"] is not None:
        mmf_vs_rrp = mmf["latest"] - rrp["latest"]
    rows.append(
        _row(
            "MMF vs RRP",
            mmf_vs_rrp,
            "혼합(저빈도+일간)",
            "Derived(optional)",
            mmf["date"] or rrp["date"],
            note="주기 불일치 가능, 참고용",
            suffix="B",
        )
    )

    rows.append(
        _row(
            "MMF 주간 증감",
            week_delta(mmf["latest"], mmf["previous"]),
            "저빈도",
            "FRED(optional)",
            mmf["date"],
            note="발표 주기상 N/A가 자주 발생 가능",
            suffix="B",
        )
    )

    rows.append(_row("하이일드 스프레드", hy["latest"], "일간", "FRED", hy["date"], suffix="%"))
    rows.append(_row("금융스트레스지수", stress["latest"], "주간", "FRED", stress["date"]))

    sofr_effr = None if sofr["latest"] is None or effr["latest"] is None else sofr["latest"] - effr["latest"]
    rows.append(_row("SOFR/EFFR 스프레드", sofr_effr, "일간", "FRED(derived)", sofr["date"] or effr["date"], suffix="%"))

    sofr_iorb = None if sofr["latest"] is None or iorb["latest"] is None else sofr["latest"] - iorb["latest"]
    rows.append(
        _row(
            "SOFR/IORB 스프레드",
            sofr_iorb,
            "일간",
            "FRED(derived, optional)",
            sofr["date"] or iorb["date"],
            note="IORB 시리즈 접근 실패 시 N/A",
            suffix="%",
        )
    )

    rows.append(
        _row(
            "공포탐욕지수",
            fear["latest"],
            "장중/일간(optional)",
            "CNN(optional)",
            fear["date"],
            note="공식 API 불안정 가능, 실패 시 N/A",
        )
    )

    return rows


def to_table_dict(rows: List[IndicatorRow]) -> List[Dict[str, str]]:
    return [
        {
            "지표": r.name,
            "값": r.display_value,
            "상태": r.status,
            "주기": r.frequency,
            "최신 기준일": r.latest_date or "N/A",
            "출처": r.source,
            "비고": r.note,
        }
        for r in rows
    ]
