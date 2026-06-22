"""
stocks.py - 뉴비콘 종목 차트(TradingView) + AI 분석 섹션 생성

비용:
  - TradingView 위젯: 공식 무료 embed (https://www.tradingview.com/widget/)
  - Claude 분석: 포스트당 ~$0.01 추가
  - 외부 주가 API: 불필요 (TradingView 위젯이 실시간 데이터 표시)
"""
import re
import anthropic

DISCLAIMER = (
    "※ 이 분석은 AI가 생성한 정보 제공 목적의 콘텐츠입니다. "
    "투자 자문이 아니며, 투자 판단의 책임은 투자자 본인에게 있습니다. "
    "투자 전 반드시 공식 공시 및 전문 투자자의 의견을 확인하세요."
)


def _tradingview_widget(tv_symbol: str, widget_id: str) -> str:
    """TradingView Mini Symbol Overview Widget HTML"""
    return f"""  <div class="tradingview-widget-container" style="margin-bottom:12px;">
    <div id="{widget_id}"></div>
    <div style="font-size:.72em;color:#999;margin-top:2px;">
      <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">TradingView</a>
    </div>
    <script type="text/javascript"
      src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js"
      async>
    {{
      "symbol": "{tv_symbol}",
      "width": "100%",
      "height": 200,
      "locale": "kr",
      "dateRange": "1M",
      "colorTheme": "light",
      "isTransparent": false,
      "autosize": true
    }}
    </script>
  </div>"""


def _parse_ticker(raw: str) -> dict | None:
    """
    "NASDAQ:RKLB" 또는 "KRX:010140" 형식 파싱.
    반환: {"tv": "NASDAQ:RKLB", "exchange": "NASDAQ", "symbol": "RKLB"}
    """
    raw = raw.strip()
    if not raw or raw in ("없음", "N/A", "-"):
        return None
    if ":" in raw:
        exchange, symbol = raw.split(":", 1)
        return {"tv": raw, "exchange": exchange.upper(), "symbol": symbol.upper()}
    return {"tv": raw, "exchange": "", "symbol": raw.upper()}


def _generate_analysis(ticker_infos: list[dict], post_excerpt: str,
                       client: anthropic.Anthropic) -> str:
    """Claude로 종목 AI 분석 단락 생성"""
    if not ticker_infos:
        return ""

    ticker_list = "\n".join(
        f"- {t['exchange']}:{t['symbol']}" for t in ticker_infos
    )
    prompt = f"""우주·방산 관련 종목 분석을 한국어 블로그용으로 간략히 작성하라.

[글 본문 요약 — 분석 컨텍스트]
{post_excerpt[:1000]}

[분석 대상 종목]
{ticker_list}

[작성 규칙]
- 각 종목당 3~4문장. 전체 150~300자.
- 사업 핵심 + 최근 동향 + 투자 관심 포인트(리스크 포함).
- 말투: 친근한 평어체 (~다, ~이다).
- "매수·매도 추천" 직접 표현 절대 금지.
- 굵게(**bold**) 사용 가능. ## 헤딩 없이 본문만 출력.
- 면책 문구는 별도 추가되므로 포함 금지.

분석 텍스트만 출력."""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"  ⚠ 종목 분석 생성 오류: {e}")
        return ""


def build_stock_section(tickers_raw: list[str], post_excerpt: str,
                        client: anthropic.Anthropic) -> str:
    """
    종목 차트(TradingView) + AI 분석 + 면책 문구 HTML 블록 반환.
    tickers_raw: ["NASDAQ:RKLB", "TSX:MDA", "KRX:010140"] 형식 리스트
    post_excerpt: 글 본문 텍스트 (분석 컨텍스트용)
    반환: Gutenberg wp:html 블록 문자열 (없으면 "")
    """
    ticker_infos = [_parse_ticker(t) for t in tickers_raw]
    ticker_infos = [t for t in ticker_infos if t]

    if not ticker_infos:
        return ""

    print(f"  📊 종목 AI 분석 생성 중: {[t['tv'] for t in ticker_infos]}")

    # TradingView 위젯 HTML
    widgets_html = "\n".join(
        _tradingview_widget(t["tv"], f"tv_{i}")
        for i, t in enumerate(ticker_infos)
    )

    # AI 분석
    analysis_raw = _generate_analysis(ticker_infos, post_excerpt, client)
    if analysis_raw:
        analysis_raw = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", analysis_raw)
        paragraphs = [p.strip() for p in analysis_raw.split("\n") if p.strip()]
        analysis_html = "\n    ".join(f"<p style='margin:.6em 0;'>{p}</p>" for p in paragraphs)
    else:
        analysis_html = ""

    disclaimer_html = (
        f'<p style="font-size:.78em;color:#999;border-top:1px solid #e8e8e8;'
        f'padding-top:.7em;margin-top:1em;line-height:1.5;">{DISCLAIMER}</p>'
    )

    return f"""<!-- wp:html -->
<div style="margin:2em 0;padding:20px 20px 16px;background:#f8f9fb;border-radius:12px;border:1px solid #dde3ec;">
  <p style="font-size:1em;font-weight:700;margin:0 0 12px;color:#1a1a2e;">📊 관련 종목 차트</p>
  {widgets_html}
  <p style="font-size:1em;font-weight:700;margin:16px 0 8px;color:#1a1a2e;">🤖 AI 종목 분석</p>
  <div style="font-size:.93em;line-height:1.7;color:#333;">
    {analysis_html}
  </div>
  {disclaimer_html}
</div>
<!-- /wp:html -->"""
