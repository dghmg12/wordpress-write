"""
topic_tracker.py - 발행된 주제/키워드 추적 모듈
중복 주제 방지를 위해 최근 사용된 키워드를 기록하고 읽어온다.
"""
import json
import os
from datetime import datetime, timedelta

TRACKER_FILE = os.path.join(os.path.dirname(__file__), "used_topics.json")
KEEP_DAYS = 45   # 45일치 보관
MAX_ENTRIES = 90  # 최대 90개


def load_used_topics() -> list[dict]:
    """저장된 주제 목록 읽기"""
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_topic(keyword: str, title: str, topic: str = "", site: str = "health"):
    """발행 완료된 주제 저장"""
    if not keyword:
        return
    topics = load_used_topics()
    topics.append({
        "keyword": keyword,
        "title": title,
        "topic": topic,
        "site": site,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    # 오래된 항목 정리
    cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    topics = [t for t in topics if t.get("date", "") >= cutoff]
    topics = topics[-MAX_ENTRIES:]

    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)


def get_recent_keywords(days: int = 30, site: str = None) -> list[str]:
    """최근 N일 내 사용된 포커스 키워드 목록 반환 (사이트별 필터 가능)"""
    topics = load_used_topics()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    result = []
    for t in topics:
        if t.get("date", "") < cutoff:
            continue
        if site and t.get("site", "health") != site:
            continue
        if t.get("keyword"):
            result.append(t["keyword"])
    return result


def get_recent_titles(days: int = 30) -> list[str]:
    """최근 N일 내 발행된 제목 목록 반환"""
    topics = load_used_topics()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [t["title"] for t in topics if t.get("date", "") >= cutoff and t.get("title")]


if __name__ == "__main__":
    print("=== 최근 사용 키워드 ===")
    for kw in get_recent_keywords():
        print(f"  - {kw}")
