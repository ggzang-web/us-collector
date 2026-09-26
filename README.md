# US Collector

DART Collector의 미국판. SEC EDGAR + roic.ai 링크를 모아 HTML 한 페이지로 만든다.
(공시자료 원문을 직접 긁어오지 않고, 링크만 모아준다 — 다운로드는 DownThemAll로 직접.)

## 사용법 (GitHub Actions)
1. Actions 탭 → "US Collector" → Run workflow
2. 티커 입력 (예: TSLA)
3. 완료 후 Artifacts에서 `{TICKER}_filings_collection.html` 다운로드
4. Chrome에서 열기 → DownThemAll! 확장으로 전체 링크 다운로드

## 로컬 실행
```
pip install requests
python us_collector.py TSLA
```

## 수집 범위 (us_collector.py 상단에서 조정 가능)
- 10-K: 최근 5년
- 10-Q: 최근 8분기
- DEF 14A: 최근 1건
- 8-K: 최근 8건 (참고용)
- 어닝콜(roic.ai): 최근 12분기 (날짜 기준 추정 URL — 실제 미발표분은 404 가능)

## 주의
- USER_AGENT를 본인 이메일로 교체 권장 (us_collector.py 상단 HEADERS)
- 어닝콜 링크는 roic.ai의 실제 존재 여부를 확인하지 않고 생성한 것 (SEC와 달리 공식 API가 아님)
