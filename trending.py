"""
trending.py - Reddit / YouTube / Google Trends / Google News 콘텐츠 수집

API 키 불필요:
  - Reddit: 공개 JSON API (User-Agent만 설정)
  - YouTube: 채널 RSS 피드
  - Google Trends: 일별 트렌딩 검색어 RSS
  - Google News: 검색어 기반 RSS (최신 기사)
"""
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

# ── Reddit 서브레딧 ────────────────────────────────────────
SPACE_SUBS    = ['space', 'SpaceXLounge', 'RocketLab', 'nasa', 'aerospace']
DEFENSE_SUBS  = ['CredibleDefense', 'geopolitics', 'worldnews', 'korea']
INVEST_SUBS   = ['investing', 'stocks', 'SecurityAnalysis']

# ── YouTube 채널 (channel_id: 이름) ───────────────────────
YOUTUBE_CHANNELS = {
    'UCVTomc35agH1SM6kCKzwW_g': 'Everyday Astronaut',
    'UCtI0Hodo5o5dUb67FeUjAlg': 'SpaceX',
    'UCLA_DiR1FfKNvjuUpBHmylQ': 'NASA',
    'UCxzC4EngIsMrPmbm6Nxvb-A': 'Scott Manley',
    'UCR1IuLEqb6UEA_zQ81kwXfg': 'Real Engineering',
    'UC6uKrU_WqJ1R2HMTY3LIx5Q': 'Veritasium',       # 과학 대중화
}

HEADERS = {"User-Agent": "NewbiconSpaceBot/1.0 (blog automation, educational)"}


def fetch_reddit_trending(subreddits: list = None, days: int = 7,
                          min_score: int = 150) -> list[dict]:
    """Reddit 인기글 수집 — 최근 N일, 최소 score 이상만"""
    if subreddits is None:
        subreddits = SPACE_SUBS + DEFENSE_SUBS[:2]

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items = []

    for sub in subreddits:
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json",
                params={"limit": 25},
                headers=HEADERS,
                timeout=10,
            )
            if not resp.ok:
                continue
            for post in resp.json().get('data', {}).get('children', []):
                d = post.get('data', {})
                created = datetime.fromtimestamp(d.get('created_utc', 0), tz=timezone.utc)
                if created < cutoff:
                    continue
                score = d.get('score', 0)
                if score < min_score:
                    continue
                title = d.get('title', '').strip()
                if not title:
                    continue
                items.append({
                    'title':   title,
                    'url':     d.get('url', ''),
                    'score':   score,
                    'comments': d.get('num_comments', 0),
                    'summary': (d.get('selftext', '') or title)[:300],
                    'source':  f"Reddit r/{sub} (👍{score:,})",
                    'type':    'reddit',
                })
        except Exception as e:
            print(f"  ⚠ Reddit r/{sub}: {e}")

    items.sort(key=lambda x: x['score'], reverse=True)
    return items[:8]


def fetch_youtube_recent(channel_ids: dict = None, days: int = 7) -> list[dict]:
    """YouTube 인기 채널 최신 영상 수집 — RSS 기반, API 키 불필요"""
    if channel_ids is None:
        channel_ids = YOUTUBE_CHANNELS

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items = []

    for ch_id, ch_name in channel_ids.items():
        try:
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch_id}"
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                pub = entry.get('published_parsed')
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                title = entry.get('title', '').strip()
                link  = entry.get('link', '').strip()
                summary = BeautifulSoup(
                    entry.get('summary', ''), 'html.parser'
                ).get_text()[:200].strip()
                if title:
                    items.append({
                        'title':   title,
                        'url':     link,
                        'score':   0,
                        'summary': summary or title,
                        'source':  f"YouTube · {ch_name}",
                        'type':    'youtube',
                    })
        except Exception as e:
            print(f"  ⚠ YouTube {ch_name}: {e}")

    return items


def fetch_google_trends(geo: str = 'KR') -> list[str]:
    """Google 트렌딩 검색어 수집 — 일별 RSS"""
    try:
        feed = feedparser.parse(
            f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}"
        )
        return [e.get('title', '').strip() for e in feed.entries[:20] if e.get('title')]
    except Exception as e:
        print(f"  ⚠ Google Trends: {e}")
    return []


def fetch_all_trending(days: int = 7) -> dict:
    """Reddit + YouTube + Google Trends 통합 수집"""
    print("  📊 트렌딩 콘텐츠 수집 중...")

    reddit  = fetch_reddit_trending(days=days)
    youtube = fetch_youtube_recent(days=days)
    kr_trends = fetch_google_trends(geo='KR')
    us_trends = fetch_google_trends(geo='US')

    # 우주·방산 관련 키워드 필터링
    space_keywords = {'space', 'rocket', 'satellite', 'nasa', 'spacex', 'launch',
                      'missile', 'defense', 'asteroid', 'moon', 'mars', '우주', '방산',
                      'hanwha', 'KAI', 'starlink', 'orbit', 'drone', 'ula', 'rocketlab'}
    relevant_trends = [
        kw for kw in (kr_trends + us_trends)
        if any(s in kw.lower() for s in space_keywords)
    ]

    print(f"    Reddit 인기글: {len(reddit)}건 / YouTube 최신: {len(youtube)}건 / "
          f"Trends 관련 키워드: {len(relevant_trends)}개")

    return {
        'reddit':  reddit,
        'youtube': youtube,
        'trends':  relevant_trends or kr_trends[:5],  # 관련 없으면 한국 트렌드 상위 5개
    }


def build_trending_section(data: dict) -> str:
    """프롬프트에 삽입할 트렌딩 섹션 문자열 생성"""
    lines = ["[트렌딩 & 인기 콘텐츠 — 주제 선택 시 참고]",
             "아래 인기 콘텐츠를 참고해 독자 관심이 높은 주제를 고르되, "
             "반드시 최근 실제 뉴스와 연결된 내용이어야 한다. "
             "오래된 주제나 추측성 내용 금지.\n"]

    if data.get('reddit'):
        lines.append("▶ Reddit 인기글 (점수 높을수록 관심 높음):")
        for r in data['reddit'][:5]:
            lines.append(f"  - {r['title']} [{r['source']}]")

    if data.get('youtube'):
        lines.append("\n▶ YouTube 인기 채널 최신 영상 (최근 7일 내):")
        for y in data['youtube'][:5]:
            lines.append(f"  - {y['title']} [{y['source']}]")

    if data.get('trends'):
        lines.append("\n▶ Google Trends 관련 키워드: " + ", ".join(data['trends'][:10]))

    return "\n".join(lines)


def search_recent_articles(query: str, count: int = 6, days: int = 90) -> list[dict]:
    """Google News RSS로 최신 기사 검색 (API 키 불필요).

    Returns: [{"title": str, "summary": str, "published": str}]
    """
    url = (
        f"https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=ko&gl=KR&ceid=KR:ko"
    )
    try:
        feed = feedparser.parse(url)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        results = []
        for entry in feed.entries:
            pub = entry.get("published_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            title = entry.get("title", "").strip()
            summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()[:120]
            if title:
                results.append({
                    "title": title,
                    "summary": summary.strip(),
                    "published": entry.get("published", ""),
                })
            if len(results) >= count:
                break
        return results
    except Exception as e:
        print(f"  ⚠ Google News 검색 실패 ({query}): {e}")
        return []


def build_freshness_section(query: str, articles: list[dict]) -> str:
    """최신 기사 목록을 프롬프트용 문자열로 변환"""
    if not articles:
        return ""
    lines = [
        f"[최신 참고 자료 — '{query}' 관련 최근 기사]",
        "아래 최신 기사 제목을 참고해 현재 트렌드를 파악하고, "
        "글에 언급할 제품·서비스·팁이 여전히 유효한지 확인하라.\n",
    ]
    for a in articles:
        pub = a["published"][:16] if a["published"] else ""
        lines.append(f"  - {a['title']}" + (f" ({pub})" if pub else ""))
        if a["summary"]:
            lines.append(f"    → {a['summary']}")
    return "\n".join(lines)
