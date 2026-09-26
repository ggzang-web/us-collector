# -*- coding: utf-8 -*-
"""
US Collector - 미국 상장사 공시자료 + 어닝콜 링크 수집기
DART Collector의 미국판. 트랜스크립트/공시 "본문"을 긁어오지 않고,
SEC EDGAR와 roic.ai의 "링크"만 모아 HTML 한 페이지로 정리한다.
(타민더마켓 가이드의 sec-filing-collector-korean 스킬과 동일한 워크플로우:
 URL 수집 → HTML 생성 → DownThemAll로 사용자가 직접 다운로드 → 폴더 정리)

사용법 (GitHub Actions workflow_dispatch):
  ticker 입력 (예: TSLA) → 실행 → Artifacts에서 {TICKER}_filings_collection.html 다운로드
  → Chrome에서 열기 → DownThemAll로 전체 링크 다운로드

로컬 실행:
  python us_collector.py TSLA
"""

import sys
import json
import time
from datetime import datetime, date

import requests

HEADERS = {"User-Agent": "ggzang@gmail.com"}
SEC_SLEEP = 0.12

# 수집 범위 (기본값 - 필요시 조정)
YEARS_10K = 5          # 10-K 최근 N년
QUARTERS_10Q = 8        # 10-Q 최근 N분기 (약 2년)
QUARTERS_EARNINGS = 12  # 어닝콜 최근 N분기 (약 3년)
DEF14A_COUNT = 1        # DEF 14A(주주총회 소집통지) 최근 N건


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_cik(ticker):
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    for v in data.values():
        if v["ticker"].upper() == ticker.upper():
            return str(v["cik_str"]).zfill(10), v["title"]
    return None, None


def get_submissions(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url, headers=HEADERS)
    time.sleep(SEC_SLEEP)
    r.raise_for_status()
    return r.json()


def collect_filings(submissions, cik):
    """recent 파일링에서 원하는 폼타입만 추출, 문서 URL 생성"""
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    report_dates = recent.get("reportDate", [])

    rows = []
    for i in range(len(forms)):
        rows.append({
            "form": forms[i],
            "filing_date": dates[i],
            "report_date": report_dates[i] if i < len(report_dates) else "",
            "accession": accessions[i],
            "primary_doc": primary_docs[i],
        })

    cik_int = str(int(cik))  # 앞의 0 제거 (URL 경로용)

    def doc_url(row):
        acc_nodash = row["accession"].replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{row['primary_doc']}"

    def filter_and_sort(form_type, limit):
        matched = [r for r in rows if r["form"] == form_type]
        matched.sort(key=lambda r: r["filing_date"], reverse=True)
        out = []
        for r in matched[:limit]:
            out.append({
                "label": f"{form_type} - {r['filing_date']}" + (f" (FY {r['report_date'][:4]})" if r["report_date"] else ""),
                "url": doc_url(r),
                "filing_date": r["filing_date"],
            })
        return out

    result = {
        "10-K": filter_and_sort("10-K", YEARS_10K),
        "10-Q": filter_and_sort("10-Q", QUARTERS_10Q),
        "DEF 14A": filter_and_sort("DEF 14A", DEF14A_COUNT),
        "8-K": filter_and_sort("8-K", 8),  # 최근 8건만 참고용
    }
    return result


def calendar_quarters(n):
    """오늘 기준 최근 n개 (연도, 분기) 튜플을 최신순으로 생성"""
    today = date.today()
    y, q = today.year, (today.month - 1) // 3 + 1
    out = []
    for _ in range(n):
        out.append((y, q))
        q -= 1
        if q == 0:
            q = 4
            y -= 1
    return out


def earnings_links(ticker, n):
    """roic.ai 트랜스크립트 URL 생성 (실제 존재 여부는 확인하지 않음 - 링크만 생성)"""
    out = []
    for y, q in calendar_quarters(n):
        out.append({
            "label": f"{y} Q{q} Earnings Call",
            "url": f"https://www.roic.ai/quote/{ticker.upper()}/transcripts/{y}-year/{q}-quarter",
        })
    return out


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{ticker} 공시자료+어닝콜 모음</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "Pretendard", Arial, sans-serif; max-width: 820px; margin: 0 auto; padding: 24px; background:#0f1115; color:#eef0f3; line-height:1.6; }}
  h1 {{ font-size: 22px; }}
  .meta {{ background:#131a30; border:1px solid #252a33; border-radius:10px; padding:14px 16px; margin-bottom:20px; font-size:13.5px; }}
  .howto {{ background:#1a2333; border-left:4px solid #7fa4ff; border-radius:8px; padding:14px 16px; margin-bottom:24px; font-size:13.5px; }}
  .howto ol {{ margin:8px 0 0 18px; padding:0; }}
  .warn {{ font-size:12.5px; color:#f0b45f; margin-top:8px; }}
  h2 {{ font-size:16px; border-bottom:1px solid #252a33; padding-bottom:6px; margin-top:28px; }}
  .badge {{ display:inline-block; font-size:11.5px; background:#252a33; color:#9aa1ad; padding:2px 8px; border-radius:10px; margin-left:6px; }}
  ul {{ list-style:none; padding:0; margin:10px 0; }}
  li {{ padding:6px 0; border-bottom:1px solid #1c2027; font-size:13.5px; }}
  a {{ color:#7fa4ff; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .note {{ font-size:11.5px; color:#9aa1ad; margin-top:4px; }}
</style>
</head>
<body>
  <h1>📁 {ticker} ({company_name}) 공시자료 + 어닝콜 링크 모음</h1>
  <div class="meta">
    <b>CIK:</b> {cik} &nbsp;|&nbsp; <b>생성일:</b> {generated}<br>
    <b>수집 범위:</b> 10-K 최근 {years_10k}년 · 10-Q 최근 {q_10q}분기 · DEF 14A 최근 {def14a}건 · 8-K 최근 8건(참고용) · 어닝콜 최근 {q_earnings}분기(추정 URL)
  </div>

  <div class="howto">
    <b>사용 방법</b>
    <ol>
      <li>이 HTML 파일을 Chrome에서 연다</li>
      <li>DownThemAll! 확장 아이콘 클릭 → "DownThemAll!" → 모든 링크 체크 → Download</li>
      <li>다운로드 완료 후 원하는 폴더로 정리</li>
    </ol>
    <div class="warn">⚠ 어닝콜(roic.ai) 링크는 분기 번호를 날짜 기준으로 추정 생성한 것으로, 실제 페이지가 없을 수 있습니다(아직 실적 미발표 등). 404가 뜨면 무시하고 넘어가세요.</div>
    <div class="warn">⚠ SEC 공시 링크는 EDGAR 원문 그대로이며 제3자 저작물이 아닙니다. 어닝콜 트랜스크립트 페이지는 roic.ai가 정리한 콘텐츠이므로, 페이지 내용을 그대로 재배포하지 말고 개인 리서치 용도로만 사용하세요.</div>
  </div>

  {sections}

  <h2>Sources</h2>
  <ul>
    <li><a href="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K" target="_blank">SEC EDGAR — {ticker} 전체 공시 목록</a></li>
    <li><a href="https://www.roic.ai/quote/{ticker}/transcripts" target="_blank">roic.ai — {ticker} 어닝콜 트랜스크립트 목록</a></li>
  </ul>
</body>
</html>
"""

SECTION_TEMPLATE = """
  <h2>{title} <span class="badge">{count}개</span></h2>
  <ul>
    {items}
  </ul>
"""


def build_section(title, items):
    if not items:
        return SECTION_TEMPLATE.format(title=title, count=0, items="<li class='note'>해당 없음</li>")
    lis = "\n    ".join(f'<li><a href="{it["url"]}" target="_blank">{it["label"]}</a></li>' for it in items)
    return SECTION_TEMPLATE.format(title=title, count=len(items), items=lis)


def main():
    if len(sys.argv) < 2:
        print("사용법: python us_collector.py TICKER")
        sys.exit(1)
    ticker = sys.argv[1].upper()

    log(f"{ticker} CIK 조회 중...")
    cik, company_name = get_cik(ticker)
    if not cik:
        log(f"티커 {ticker}를 찾을 수 없습니다.")
        sys.exit(1)
    log(f"찾음: {company_name} (CIK {cik})")

    log("공시 목록 조회 중...")
    submissions = get_submissions(cik)
    filings = collect_filings(submissions, cik)

    log("어닝콜 링크 생성 중 (roic.ai, 추정)...")
    earnings = earnings_links(ticker, QUARTERS_EARNINGS)

    sections = ""
    sections += build_section("10-K (연간보고서)", filings["10-K"])
    sections += build_section("10-Q (분기보고서)", filings["10-Q"])
    sections += build_section("DEF 14A (주주총회 소집통지)", filings["DEF 14A"])
    sections += build_section("8-K (수시공시, 참고용)", filings["8-K"])
    sections += build_section("Earnings Call Transcripts (roic.ai)", earnings)

    html = HTML_TEMPLATE.format(
        ticker=ticker,
        company_name=company_name,
        cik=str(int(cik)),
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        years_10k=YEARS_10K,
        q_10q=QUARTERS_10Q,
        def14a=DEF14A_COUNT,
        q_earnings=QUARTERS_EARNINGS,
        sections=sections,
    )

    out_path = f"{ticker}_filings_collection.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"완료: {out_path}")


if __name__ == "__main__":
    main()
