"""Indicator computation and risk classification rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from config import AppConfig, FRED_SERIES, FRED_SERIES_CANDIDATES
from data_sources import fetch_fear_greed_optional, fetch_fred_first_available, fetch_fred_latest
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


def to_billions(value: Optional[float], source_unit: str = "million") -> Optional[float]:
    if value is None:
        return None
    if source_unit == "million":
        return value / 1000.0
    return value


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _older_date(*date_strs: Optional[str]) -> Optional[str]:
    parsed = [d for d in (_parse_date(x) for x in date_strs) if d is not None]
    if not parsed:
        return None
    return min(parsed).isoformat()


def _max_age_days(frequency: str) -> int:
    if "장중" in frequency:
        return 3
    if "일간" in frequency:
        return 7
    if "주간" in frequency:
        return 21
    if "저빈도" in frequency:
        return 120
    if "혼합" in frequency:
        return 120
    return 30


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


def _refresh_rules() -> Dict[str, int]:
    return {
        "일간": 7,
        "주간": 21,
        "일간/주간": 21,
        "저빈도(월/분기 가능)": 120,
        "저빈도": 120,
        "혼합(저빈도+일간)": 120,
        "장중/일간(optional)": 3,
    }


def apply_freshness_checks(rows: List[IndicatorRow]) -> List[IndicatorRow]:
    today = date.today()
    checked: List[IndicatorRow] = []
    rules = _refresh_rules()

    for row in rows:
        if row.value is None:
            checked.append(row)
            continue

        d = _parse_date(row.latest_date)
        max_age = rules.get(row.frequency, _max_age_days(row.frequency))

        if d is None:
            checked.append(
                IndicatorRow(
                    name=row.name,
                    value=row.value,
                    display_value=row.display_value,
                    status="주의",
                    frequency=row.frequency,
                    source=row.source,
                    latest_date=row.latest_date,
                    note=(row.note + " | " if row.note else "") + "데이터 지연: 기준일 파싱 실패",
                )
            )
            continue

        age = (today - d).days
        if age <= max_age:
            checked.append(row)
            continue

        optional_or_low = ("optional" in row.source.lower()) or ("저빈도" in row.frequency)
        if optional_or_low and age <= max_age * 3:
            checked.append(
                IndicatorRow(
                    name=row.name,
                    value=row.value,
                    display_value=row.display_value,
                    status="주의",
                    frequency=row.frequency,
                    source=row.source,
                    latest_date=row.latest_date,
                    note=(row.note + " | " if row.note else "") + f"데이터 지연: {age}일 경과",
                )
            )
        else:
            checked.append(
                IndicatorRow(
                    name=row.name,
                    value=None,
                    display_value="N/A",
                    status="N/A",
                    frequency=row.frequency,
                    source=row.source,
                    latest_date=row.latest_date,
                    note=(row.note + " | " if row.note else "") + f"데이터 지연: {age}일 경과로 N/A",
                )
            )
    return checked


def build_indicators(config: AppConfig) -> List[IndicatorRow]:
    rows: List[IndicatorRow] = []

    vix = fetch_fred_latest(FRED_SERIES["vix"], config, max_age_days=10)
    yc = fetch_fred_latest(FRED_SERIES["yield_curve_10y2y"], config, max_age_days=14)
    walcl = fetch_fred_latest(FRED_SERIES["fed_balance_sheet"], config, max_age_days=35)
    reserves = fetch_fred_first_available(FRED_SERIES_CANDIDATES["reserve_balances"], config, max_age_days=35)
    rrp = fetch_fred_latest(FRED_SERIES["rrp"], config, max_age_days=14)
    tga = fetch_fred_latest(FRED_SERIES["tga"], config, max_age_days=35)
    hy = fetch_fred_latest(FRED_SERIES["hy_spread"], config, max_age_days=14)
    stress = fetch_fred_latest(FRED_SERIES["financial_stress"], config, max_age_days=35)
    sofr = fetch_fred_latest(FRED_SERIES["sofr"], config, max_age_days=10)
    effr = fetch_fred_latest(FRED_SERIES["effr"], config, max_age_days=10)
    iorb = fetch_fred_latest(FRED_SERIES["iorb"], config, max_age_days=14)
    mmf = fetch_fred_latest(FRED_SERIES["mmf_total_assets"], config, max_age_days=180)
    fear = fetch_fear_greed_optional()

    walcl_b = to_billions(walcl["latest"], "million")
    reserves_b = to_billions(reserves["latest"], "million")
    reserves_prev_b = to_billions(reserves["previous"], "million")
    tga_b = to_billions(tga["latest"], "million")
    tga_prev_b = to_billions(tga["previous"], "million")

    rows.append(_row("VIX", vix["latest"], "일간", "FRED", vix["date"]))
    rows.append(_row("장단기 금리차 (10Y-2Y)", yc["latest"], "일간", "FRED", yc["date"], suffix="%"))
    rows.append(_row("연준 대차대조표", walcl_b, "주간", "FRED", walcl["date"], note="WALCL 백만→십억 달러 변환", suffix="B"))
    reserve_sid = reserves.get("series_id") or FRED_SERIES["reserve_balances"]
    # 중점 점검 항목: 지급준비금/지급준비금 주간 증감/TGA/TGA 주간 증감
    rows.append(_row("지급준비금", reserves_b, "주간", "FRED", reserves["date"], note=f"{reserve_sid} 백만→십억 달러 변환", suffix="B"))
    rows.append(_row("역레포(RRP)", rrp["latest"], "일간", "FRED", rrp["date"], suffix="B"))
    rows.append(_row("TGA", tga_b, "일간/주간", "FRED", tga["date"], note="WTREGEN 백만→십억 달러 변환", suffix="B"))

    rows.append(_row("지급준비금 주간 증감", week_delta(reserves_b, reserves_prev_b), "주간", "FRED", reserves["date"], note=f"기준 시리즈: {reserve_sid}", suffix="B"))
    rows.append(_row("TGA 주간 증감", week_delta(tga_b, tga_prev_b), "주간", "FRED", tga["date"], suffix="B"))

    mmf_b = to_billions(mmf["latest"], "million")
    mmf_prev_b = to_billions(mmf["previous"], "million")
    rows.append(_row("MMF 총 잔액", mmf_b, "저빈도(월/분기 가능)", "FRED(optional)", mmf["date"], note="저빈도/시리즈 변경 가능, 백만→십억 달러 변환", suffix="B"))

    mmf_vs_rrp = None if mmf_b is None or rrp["latest"] is None else mmf_b - rrp["latest"]
    rows.append(_row("MMF vs RRP", mmf_vs_rrp, "혼합(저빈도+일간)", "Derived(optional)", _older_date(mmf["date"], rrp["date"]), note="혼합 주기: 더 오래된 기준일 사용", suffix="B"))

    rows.append(_row("MMF 주간 증감", week_delta(mmf_b, mmf_prev_b), "저빈도", "FRED(optional)", mmf["date"], note="저빈도라 N/A 가능", suffix="B"))
    rows.append(_row("하이일드 스프레드", hy["latest"], "일간", "FRED", hy["date"], suffix="%"))
    rows.append(_row("금융스트레스지수", stress["latest"], "주간", "FRED", stress["date"]))

    sofr_effr = None if sofr["latest"] is None or effr["latest"] is None else sofr["latest"] - effr["latest"]
    rows.append(_row("SOFR/EFFR 스프레드", sofr_effr, "일간", "FRED(derived)", _older_date(sofr["date"], effr["date"]), note="파생지표: 더 오래된 기준일 사용", suffix="%"))

    sofr_iorb = None if sofr["latest"] is None or iorb["latest"] is None else sofr["latest"] - iorb["latest"]
    rows.append(_row("SOFR/IORB 스프레드", sofr_iorb, "일간", "FRED(derived, optional)", _older_date(sofr["date"], iorb["date"]), note="IORB 실패/지연 시 N/A", suffix="%"))

    rows.append(_row("공포탐욕지수", fear["latest"], "장중/일간(optional)", "CNN(optional)", fear["date"], note="공식 API 불안정 가능"))

    return apply_freshness_checks(rows)


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
