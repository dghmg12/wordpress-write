"""
crawler.py - 웹 크롤링 및 RSS 피드 수집 모듈
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os

# 기본 RSS 피드 목록 (환경변수로 덮어쓰기 가능)
DEFAULT_RSS_FEEDS = [
    "https://kormedi.com/feed/",                    # 코메디닷컴 (건강 전문)
    "https://www.mk.co.kr/rss/40300001/",           # 매일경제 건강/의료
    "https://www.yna.co.kr/rss/health.xml",         # 연합뉴스 건강
    "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=08",  # SBS 건강
    "https://rss.donga.com/total.xml",              # 동아일보 (종합)
]

def get_rss_feeds():
    """환경변수 또는 기본값에서 RSS 피드 목록 가져오기"""
    env_feeds = os.environ.get("RSS_FEEDS", "")
    if env_feeds.strip():
        return [f.strip() for f in env_feeds.split(",") if f.strip()]
    return DEFAULT_RSS_FEEDS


def get_keywords():
    """크롤링 필터링 키워드 목록"""
    env_kw = os.environ.get("CRAWL_KEYWORDS", "")
    if env_kw.strip():
        return [k.strip() for k in env_kw.split(",") if k.strip()]
    return []  # 빈 리스트면 전체 수집


def fetch_rss_articles(max_per_feed: int = 5, feeds: list[str] = None) -> list[dict]:
    """
    RSS 피드에서 최근 기사 수집
    반환: [{"title": ..., "url": ..., "summary": ..., "source": ...}, ...]
    """
    feeds = feeds or get_rss_feeds()
    keywords = get_keywords()
    articles = []

    for feed_url in feeds:
        try:
            print(f"  RSS 수집 중: {feed_url}")
            feed = feedparser.parse(feed_url)
            count = 0

            for entry in feed.entries:
                if count >= max_per_feed:
                    break

                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()

                # BeautifulSoup으로 HTML 태그 제거
                summary = BeautifulSoup(summary, "html.parser").get_text()
                summary = summary[:300].strip()  # 300자 이하로 자르기

                # 키워드 필터링 (설정된 경우)
                if keywords:
                    matched = any(kw in title or kw in summary for kw in keywords)
                    if not matched:
                        continue

                articles.append({
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "source": feed.feed.get("title", feed_url),
                })
                count += 1

        except Exception as e:
            print(f"  ⚠ RSS 수집 실패 ({feed_url}): {e}")

    print(f"  총 {len(articles)}개 기사 수집 완료")
    return articles


def fetch_article_body(url: str, max_chars: int = 2000) -> str:
    """
    기사 URL에서 본문 텍스트 추출
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
            tag.decompose()

        # 본문 후보 태그 순서대로 시도
        for selector in ["article", "main", ".article-body", ".news-content", "#content", "body"]:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n").strip()
                # 빈 줄 정리
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                text = "\n".join(lines)
                return text[:max_chars]

    except Exception as e:
        print(f"  ⚠ 본문 추출 실패 ({url}): {e}")

    return ""


if __name__ == "__main__":
    # 테스트 실행
    from dotenv import load_dotenv
    load_dotenv()

    print("=== 크롤링 테스트 ===")
    articles = fetch_rss_articles(max_per_feed=3)
    for a in articles[:3]:
        print(f"\n제목: {a['title']}")
        print(f"출처: {a['source']}")
        print(f"요약: {a['summary'][:100]}...")
