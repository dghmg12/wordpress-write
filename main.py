"""
main.py - 자동 크롤링 → 글 작성 → WordPress 발행 메인 실행 파일

사용법:
  py main.py                          # 기본 (health 사이트, 오늘 주제 자동)
  py main.py --site economy           # newbicon.com (경제/부동산/투자)
  py main.py --site health            # blacknudge.com (건강/운동/식단)
  py main.py --site economy --test-wp # 연결 테스트
  py main.py --site economy --dry-run # 글 미리보기
  py main.py --site economy --topic 부동산  # 주제 직접 지정
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os
import argparse
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

KST = timezone(timedelta(hours=9))


def run_full_pipeline(site_cfg: dict, topic: str = "", dry_run: bool = False):
    """
    전체 파이프라인 실행:
    1. 크롤링 (사이트별 RSS)
    2. Claude API로 글 작성 (중복 키워드 회피)
    3. WordPress 발행 (사이트별 계정)
    """
    from crawler import fetch_rss_articles
    from writer import write_article
    from wordpress import publish_post
    from images import fetch_multiple_images
    from topic_tracker import get_recent_keywords, save_topic

    site_key = site_cfg["_key"]
    today = datetime.now(KST)
    if not topic:
        topic = site_cfg["topics"].get(today.weekday(), list(site_cfg["topics"].values())[0])

    print(f"\n{'='*50}")
    print(f"  자동 포스팅 시작")
    print(f"  사이트: {site_cfg['name']}")
    print(f"  날짜: {today.strftime('%Y-%m-%d %H:%M')} KST")
    print(f"  주제: {topic}")
    print(f"{'='*50}\n")

    # Step 1: 크롤링 (사이트별 RSS 피드)
    print("📰 [1/3] 기사 수집 중...")
    articles = fetch_rss_articles(max_per_feed=5, feeds=site_cfg["rss_feeds"])
    if not articles:
        print("  ⚠ 수집된 기사가 없습니다. 주제만으로 글을 작성합니다.")

    # Step 2: 글 작성 (사이트별 키워드 중복 방지)
    used_keywords = get_recent_keywords(days=30, site=site_key)
    if used_keywords:
        print(f"  최근 30일 사용 키워드 {len(used_keywords)}개 회피 적용")
    print(f"\n✍️  [2/3] 글 작성 중 (Claude API)...")
    result = write_article(
        articles,
        topic=topic,
        used_keywords=used_keywords,
        style_hint=site_cfg.get("style_hint", ""),
        style_desc=site_cfg.get("style_desc", ""),
        link_sources=site_cfg.get("link_sources", []),
        site_label=site_cfg.get("style_hint", ""),
    )

    print(f"\n  제목: {result['title']}")
    print(f"  본문: {len(result['content_markdown'])}자")
    print(f"  태그: {', '.join(result['tags'])}")
    print(f"  포커스 키워드: {result.get('focus_keyword', '-')}")
    print(f"  SEO 제목: {result.get('seo_title', '-')}")
    print(f"  발췌: {result['excerpt'][:60]}...")

    # Step 2.5: 이미지 검색 (대표 1장 + 본문 3장 = 총 4장)
    image_query = result.get("image_query", topic or result["title"][:20])
    print(f"\n🖼  [2.5/3] 이미지 검색 중 (키워드: {image_query}, 4장)...")
    image_list = fetch_multiple_images(image_query, count=4)
    if image_list:
        print(f"  이미지 {len(image_list)}장 찾음: {image_list[0]['credit']}")
        featured_image = image_list[0]      # 첫 번째: 대표 이미지 전용
        body_images    = image_list[1:]     # 나머지 3장: 본문 삽입용
    else:
        featured_image = None
        body_images    = []
        print("  이미지 없이 진행합니다.")

    # Step 3: WordPress 발행
    if dry_run:
        print(f"\n🚫 [3/3] --dry-run 모드: 발행 건너뜀")
        print("\n--- 생성된 본문 미리보기 (앞 500자) ---")
        print(result["content_markdown"][:500])
        print("...")
        if featured_image:
            print(f"\n🖼 대표 이미지: {featured_image['credit']}")
        if body_images:
            print(f"🖼 본문 이미지 {len(body_images)}장 준비됨")
        return result

    print(f"\n🚀 [3/3] WordPress에 발행 중...")
    wp_env = {
        "wp_url_env": site_cfg["wp_url_env"],
        "wp_user_env": site_cfg["wp_user_env"],
        "wp_pass_env": site_cfg["wp_pass_env"],
    }
    post_result = publish_post(
        title=result["title"],
        content_html=result["content_html"],
        excerpt=result["excerpt"],
        tags=result["tags"],
        featured_image_url=featured_image["url"] if featured_image else None,
        image_list=body_images,             # 본문용 3장 (대표 이미지와 별개)
        focus_keyword=result.get("focus_keyword", ""),
        seo_title=result.get("seo_title", ""),
        seo_description=result.get("seo_description", ""),
        image_alt=result.get("focus_keyword", result["title"]),
        wp_env=wp_env,
    )

    # 발행 성공 시 사이트별 키워드 추적 저장
    save_topic(
        keyword=result.get("focus_keyword", ""),
        title=result["title"],
        topic=topic,
        site=site_key,
    )

    print(f"\n{'='*50}")
    print(f"  ✅ 완료!")
    print(f"  포스트 ID: {post_result['id']}")
    print(f"  URL: {post_result['url']}")
    print(f"  상태: {post_result['status']}")
    print(f"{'='*50}\n")

    return post_result


def main():
    parser = argparse.ArgumentParser(description="WordPress 자동 포스팅 봇 (멀티 사이트)")
    parser.add_argument("--site", type=str, default="health",
                        help="사이트 선택: health (기본) | economy")
    parser.add_argument("--test-wp",    action="store_true", help="WordPress 연결 테스트")
    parser.add_argument("--test-crawl", action="store_true", help="크롤링 테스트")
    parser.add_argument("--dry-run",    action="store_true", help="글 생성까지만 (발행 안 함)")
    parser.add_argument("--topic",      type=str, default="", help="주제 직접 지정")
    args = parser.parse_args()

    from sites import get_site
    site_cfg = get_site(args.site)
    site_cfg["_key"] = args.site  # 내부 키 주입

    if args.test_wp:
        print(f"=== WordPress 연결 테스트 [{site_cfg['name']}] ===")
        from wordpress import test_connection
        wp_env = {
            "wp_url_env": site_cfg["wp_url_env"],
            "wp_user_env": site_cfg["wp_user_env"],
            "wp_pass_env": site_cfg["wp_pass_env"],
        }
        test_connection(wp_env=wp_env)
        return

    if args.test_crawl:
        print(f"=== 크롤링 테스트 [{site_cfg['name']}] ===")
        from crawler import fetch_rss_articles
        articles = fetch_rss_articles(max_per_feed=3, feeds=site_cfg["rss_feeds"])
        for i, a in enumerate(articles[:5], 1):
            print(f"\n[{i}] {a['title']}")
            print(f"    출처: {a['source']}")
            print(f"    요약: {a['summary'][:100]}...")
        return

    run_full_pipeline(site_cfg, topic=args.topic, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
