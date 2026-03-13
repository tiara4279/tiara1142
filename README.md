# 미국 유동성·리스크 대시보드 (Streamlit)

미국 유동성과 리스크 상태를 **최신 공개 데이터(latest available)** 기준으로 점검하는 실무형 대시보드입니다.

> 이 앱은 **실시간 트레이딩 도구가 아닙니다.** 각 지표 발표 주기(장중/일간/주간/저빈도)가 다르며, 최신 공개치 기준으로 표시합니다.

## 구성 파일

- `app.py`
- `data_sources.py`
- `indicators.py`
- `utils.py`
- `config.py`
- `requirements.txt`
- `.env.example`

## 설치 방법

```bash
pip install -r requirements.txt
```

## FRED API KEY 설정 방법

1. FRED API Key 발급: https://fred.stlouisfed.org/docs/api/api_key.html
2. `.env.example`를 복사해 `.env` 생성
3. 아래 값 입력

```env
FRED_API_KEY=your_fred_api_key_here
```

## 실행 방법

```bash
streamlit run app.py
```

## 주요 기능

- 상단 요약 대시보드(전체 지표/수집 성공/주의/위험)
- 지표별 카드 표시
- 전체 표 표시
- CSV 다운로드
- 상태(안정/주의/위험/N.A.) 표시
- 마지막 갱신 시각 표시
- 일부 데이터 실패 시에도 앱 전체 동작(N/A 처리)
- 오래된 데이터 감지 시 N/A 또는 경고 표시

## 지표 목록

1. VIX
2. 장단기 금리차 (10Y-2Y)
3. 연준 대차대조표
4. 지급준비금
5. 역레포(RRP)
6. TGA
7. 지급준비금 주간 증감
8. TGA 주간 증감
9. MMF 총 잔액
10. MMF vs RRP
11. MMF 주간 증감
12. 하이일드 스프레드
13. 금융스트레스지수
14. SOFR/EFFR 스프레드
15. SOFR/IORB 스프레드
16. 공포탐욕지수(optional)

## 참고 사항

- Fear & Greed, MMF 관련(총잔액/증감/MMF vs RRP), IORB는 데이터 소스 불안정/저빈도/시리즈 변경 가능성이 있어 **optional/N.A. 허용 구조**입니다.
- 일부 FRED series id는 환경/정의 변경에 따라 실패할 수 있습니다. 코드에 `TODO` 주석으로 표시했습니다.
- yfinance는 현재 필수 경로에 포함되지 않으며, 필요 시 보조 소스로 확장 가능합니다.

- TGA는 FRED 원자료가 백만 달러 단위로 제공되는 경우가 있어 앱에서 **십억 달러(B)** 로 변환해 표시합니다.

- 모든 지표는 기준일을 전수 점검하며, 주기 대비 과도하게 오래된 데이터는 자동으로 경고 또는 N/A 처리합니다.

## 최신 공개 데이터/기준일 점검 로직

- FRED 조회 시 `observation_end=today`를 사용하고, 지표별 허용 지연일(`max_age_days`) 내 관측치만 채택합니다.
- 파생 지표(SOFR/EFFR, SOFR/IORB, MMF vs RRP)는 구성요소 중 **더 오래된 날짜**를 기준일로 표시해 날짜 과대평가를 방지합니다.
- 허용 지연일을 초과하면 `데이터 지연` 경고(주의) 또는 `N/A`로 자동 강등됩니다.
- 금액형 핵심 지표 중 `WALCL`, `WRESBAL`, `WTREGEN`은 백만 달러 값을 십억 달러(B)로 변환해 표기합니다.
