from __future__ import annotations

import pandas as pd
import streamlit as st

from config import get_config
from indicators import build_indicators, to_table_dict
from utils import now_utc_str, status_badge

st.set_page_config(page_title="US Liquidity & Risk Monitor", layout="wide")

st.title("미국 금융시장 유동성 & 리스크 모니터")
st.caption("실시간이 아닌 최신 공개 데이터(latest available) 기준 대시보드")

config = get_config()
rows = build_indicators(config)

valid_count = sum(1 for r in rows if r.value is not None)
risk_count = sum(1 for r in rows if r.status == "위험")
warn_count = sum(1 for r in rows if r.status == "주의")

c1, c2, c3, c4 = st.columns(4)
c1.metric("전체 지표", len(rows))
c2.metric("데이터 수집 성공", valid_count)
c3.metric("주의", warn_count)
c4.metric("위험", risk_count)

st.markdown("### 지표별 카드")
cols = st.columns(4)
for i, r in enumerate(rows):
    with cols[i % 4]:
        st.markdown(
            f"""
            <div style='border:1px solid #e6e6e6;border-radius:12px;padding:12px;margin-bottom:10px;'>
              <div style='font-size:0.9rem;color:#666'>{r.frequency}</div>
              <div style='font-weight:700;margin:6px 0'>{r.name}</div>
              <div style='font-size:1.2rem'>{r.display_value}</div>
              <div style='margin-top:6px'>{status_badge(r.status)}</div>
              <div style='font-size:0.8rem;color:#777;margin-top:6px'>기준일: {r.latest_date or 'N/A'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("### 전체 표")
df = pd.DataFrame(to_table_dict(rows))
st.dataframe(df, use_container_width=True, hide_index=True)

csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "CSV 다운로드",
    data=csv_bytes,
    file_name="us_liquidity_risk_dashboard.csv",
    mime="text/csv",
)

st.markdown("---")
st.write(f"마지막 갱신 시각: **{now_utc_str()}**")
st.caption(
    "일부 지표(Fear & Greed, MMF 계열, IORB 등)는 소스 불안정/저빈도/시리즈 변경으로 N/A가 발생할 수 있습니다."
)
