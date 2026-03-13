# 미국 유동성 일일 대시보드

## 왜 미리보기에서 `Not Found`가 뜨나요?
보통 아래 3가지가 원인입니다.
1. GitHub Pages 배포가 아직 끝나기 전(수 분 지연)
2. Pages 소스가 `root`/`docs`와 실제 파일 위치가 다를 때
3. 미리보기 URL이 `/`가 아니라 다른 경로로 열릴 때

이 저장소는 위 문제를 줄이기 위해 아래를 자동 생성합니다.
- `index.html` + `docs/index.html`
- `404.html` + `docs/404.html`
- `.nojekyll` + `docs/.nojekyll`

그래서 `/` 또는 `/index.html` 어느 경로로 열어도 화면이 보이도록 구성했습니다.

## 포함 지표 (15개)
1. 공포탐욕지수
2. VIX
3. 장단기 금리차(10Y-2Y)
4. 연준 대차대조표
5. 지급준비금
6. 역레포(RRP)
7. TGA
8. 주간 증감폭(지급준비금/TGA)
9. MMF 총 잔액
10. MMF vs 역레포(12주 상관계수)
11. MMF 주간 증감
12. 하이일드 스프레드
13. 금융스트레스지수
14. SOFR/EFFR 스프레드
15. SOFR/IORB 스프레드

## 실행
```bash
python daily_liquidity_dashboard.py
```

## 생성 파일
- `index.html`, `404.html`, `.nojekyll`
- `docs/index.html`, `docs/404.html`, `docs/.nojekyll`
- `data/latest_metrics.json`, `docs/latest_metrics.json`

## 자동 갱신
`.github/workflows/daily-dashboard.yml`이 매일 UTC 22:10(한국시간 07:10) 실행됩니다.

## 안정성
- 데이터 소스 일시 장애 시 스크립트는 중단되지 않습니다.
- 새 값이 `N/A`면 직전 정상값을 캐시로 유지합니다.
