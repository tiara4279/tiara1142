#!/usr/bin/env python3
"""미국 유동성/리스크 15개 지표를 매일 수집해 대시보드 파일로 저장합니다."""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import pathlib
import statistics
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

ROOT = pathlib.Path(__file__).resolve().parent
OUT_DIR = ROOT / "docs"
DATA_DIR = ROOT / "data"
JSON_PATH = DATA_DIR / "latest_metrics.json"
DOCS_JSON_PATH = OUT_DIR / "latest_metrics.json"
PUBLIC_DIR = ROOT / "public"
PUBLIC_JSON_PATH = PUBLIC_DIR / "latest_metrics.json"


@dataclass
class Metric:
    key: str
    title: str
    description: str
    value: str
    source: str


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_fred_series(series_id: str) -> list[tuple[dt.date, float]]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series_id)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = csv.DictReader(resp.read().decode("utf-8").splitlines())
        parsed: list[tuple[dt.date, float]] = []
        for row in rows:
            value = row.get(series_id) or row.get("VALUE")
            if value in (None, ".", ""):
                continue
            try:
                parsed.append((dt.date.fromisoformat(row["DATE"]), float(value)))
            except (ValueError, KeyError):
                continue
        return parsed


def latest(series: list[tuple[dt.date, float]]) -> float:
    return series[-1][1] if series else float("nan")


def fmt_number(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}" if math.isfinite(value) else "N/A"


def weekly_delta(series: list[tuple[dt.date, float]]) -> float:
    return series[-1][1] - series[-2][1] if len(series) >= 2 else float("nan")


def rolling_corr(a: list[tuple[dt.date, float]], b: list[tuple[dt.date, float]], n: int = 12) -> float:
    map_a = {d: v for d, v in a}
    common = [(map_a[d], v) for d, v in b if d in map_a]
    if len(common) < n:
        return float("nan")
    x = [v[0] for v in common[-n:]]
    y = [v[1] for v in common[-n:]]
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    vx = sum((xi - mx) ** 2 for xi in x)
    vy = sum((yi - my) ** 2 for yi in y)
    return cov / math.sqrt(vx * vy) if vx and vy else float("nan")


def safe_series(series_id: str) -> list[tuple[dt.date, float]]:
    try:
        return fetch_fred_series(series_id)
    except Exception:
        return []


def fear_greed_metric() -> Metric:
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    value = "N/A"
    try:
        payload = fetch_json(url)
        value = f"{payload['fear_and_greed']['score']} ({payload['fear_and_greed']['rating']})"
    except Exception:
        pass
    return Metric("fear_greed", "공포탐욕지수", "지금 시장이 공포인지 탐욕인지", value, url)


def build_metrics() -> list[Metric]:
    ids = [
        "VIXCLS", "T10Y2Y", "WALCL", "WRESBAL", "RRPONTSYD", "WTREGEN",
        "WMMFSL", "BAMLH0A0HYM2", "STLFSI4", "SOFR", "EFFR", "IORB",
    ]
    fred = {sid: safe_series(sid) for sid in ids}
    sofr, effr, iorb = latest(fred["SOFR"]), latest(fred["EFFR"]), latest(fred["IORB"])

    return [
        fear_greed_metric(),
        Metric("vix", "VIX", "옵션 시장 기대 변동성", fmt_number(latest(fred["VIXCLS"])), "FRED:VIXCLS"),
        Metric("curve", "장단기 금리차 (10Y-2Y)", "미국 경기침체 선행 지표", f"{fmt_number(latest(fred['T10Y2Y']))}%", "FRED:T10Y2Y"),
        Metric("walcl", "연준 대차대조표", "연준 총자산(백만 달러)", fmt_number(latest(fred["WALCL"]), 0), "FRED:WALCL"),
        Metric("reserves", "지급준비금", "연준 예치 준비금(백만 달러)", fmt_number(latest(fred["WRESBAL"]), 0), "FRED:WRESBAL"),
        Metric("rrp", "역레포(RRP)", "ON RRP 총액(십억 달러)", fmt_number(latest(fred["RRPONTSYD"])), "FRED:RRPONTSYD"),
        Metric("tga", "TGA", "미 재무부 일반계정(백만 달러)", fmt_number(latest(fred["WTREGEN"]), 0), "FRED:WTREGEN"),
        Metric("weekly_liquidity", "주간 증감폭", "지급준비금/ TGA 전주 대비", f"준비금 {fmt_number(weekly_delta(fred['WRESBAL']), 0)}, TGA {fmt_number(weekly_delta(fred['WTREGEN']), 0)}", "FRED:WRESBAL,WTREGEN"),
        Metric("mmf_total", "MMF 총 잔액", "머니마켓펀드 총자산(십억 달러)", fmt_number(latest(fred["WMMFSL"])), "FRED:WMMFSL"),
        Metric("mmf_rrp", "MMF vs 역레포", "최근 12주 상관계수", fmt_number(rolling_corr(fred["WMMFSL"], fred["RRPONTSYD"]), 3), "Calc:WMMFSL,RRPONTSYD"),
        Metric("mmf_delta", "MMF 주간 증감", "전주 대비 증감(십억 달러)", fmt_number(weekly_delta(fred["WMMFSL"])), "FRED:WMMFSL"),
        Metric("hy_spread", "하이일드 스프레드", "정크본드 OAS(%)", fmt_number(latest(fred["BAMLH0A0HYM2"])), "FRED:BAMLH0A0HYM2"),
        Metric("stress", "금융스트레스지수", "세인트루이스 연은 금융스트레스", fmt_number(latest(fred["STLFSI4"]), 3), "FRED:STLFSI4"),
        Metric("sofr_effr", "SOFR/EFFR 스프레드", "담보부-무담보 단기금리", f"{fmt_number(sofr - effr, 3)}%", "Calc:SOFR,EFFR"),
        Metric("sofr_iorb", "SOFR/IORB 스프레드", "시장금리-연준 기준금리", f"{fmt_number(sofr - iorb, 3)}%", "Calc:SOFR,IORB"),
    ]


def merge_with_previous(metrics: list[Metric]) -> list[Metric]:
    if not JSON_PATH.exists():
        return metrics
    try:
        prev = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        prev_map = {m["key"]: m for m in prev.get("metrics", [])}
    except Exception:
        return metrics

    merged: list[Metric] = []
    for m in metrics:
        if "N/A" not in m.value:
            merged.append(m)
            continue
        old = prev_map.get(m.key)
        if old and old.get("value") and "N/A" not in old["value"]:
            merged.append(Metric(m.key, m.title, m.description, old["value"], f"{m.source} (cached)"))
        else:
            merged.append(m)
    return merged


def render_html(payload: dict) -> str:
    cards = "\n".join(
        f"<div class='card'><h3>{m['title']}</h3><p class='desc'>{m['description']}</p><p class='value'>{m['value']}</p><p class='src'>{m['source']}</p></div>"
        for m in payload["metrics"]
    )
    return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/><title>미국 유동성 일일 대시보드</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#0b1220;color:#e5e7eb}}header{{padding:24px;border-bottom:1px solid #243043}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;padding:24px}}.card{{background:#111b2e;border:1px solid #243043;border-radius:12px;padding:16px}}h3{{margin:0 0 8px;font-size:18px}}.desc{{margin:0 0 12px;font-size:13px;color:#93a4bd}}.value{{margin:0 0 10px;font-size:24px;font-weight:700}}.src{{margin:0;font-size:11px;color:#6b7f9e}}.tip{{font-size:13px;color:#a3b5cf}}</style></head>
<body><header><h1>미국 연준 기반 15개 지표 대시보드</h1><p>마지막 갱신(UTC): {payload['generated_at_utc']}</p><p class='tip'>미리보기에서 Not Found가 뜨면 잠시 후 새로고침하거나 /index.html 경로로 접속하세요.</p></header><section class='grid'>{cards}</section></body></html>"""


def write_support_files(html: str) -> None:
    for target in [ROOT / "404.html", OUT_DIR / "404.html", PUBLIC_DIR / "404.html"]:
        target.write_text(html, encoding="utf-8")
    for target in [ROOT / ".nojekyll", OUT_DIR / ".nojekyll", PUBLIC_DIR / ".nojekyll"]:
        target.write_text("", encoding="utf-8")


def main() -> None:
    payload = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "metrics": [asdict(m) for m in merge_with_previous(build_metrics())],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    html = render_html(payload)
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    (PUBLIC_DIR / "index.html").write_text(html, encoding="utf-8")
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    DOCS_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    PUBLIC_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_support_files(html)


if __name__ == "__main__":
    main()
