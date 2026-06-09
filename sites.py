"""
sites.py - 멀티 사이트 설정 관리
각 사이트별 WordPress 연결 정보, 주제, RSS 피드, 글 스타일을 정의한다.

사용법:
  py main.py --site health    # blacknudge.com (건강/운동/식단)
  py main.py --site economy   # newbicon.com (경제/부동산/투자)
"""

SITES = {
    "health": {
        "name": "blacknudge (건강/운동/식단)",
        "display_name": "블랙넛지",
        # WordPress 연결 (env 변수명)
        "wp_url_env":  "WP_URL",
        "wp_user_env": "WP_USER",
        "wp_pass_env": "WP_APP_PASSWORD",
        # 요일별 주제 (0=월 ... 6=일)
        "topics": {
            0: "운동",
            1: "식단",
            2: "건강",
            3: "운동",
            4: "식단",
            5: "건강",
            6: "운동",
        },
        # RSS 피드
        "rss_feeds": [
            "https://kormedi.com/feed/",
            "https://www.mk.co.kr/rss/40300001/",
            "https://www.yna.co.kr/rss/health.xml",
            "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=08",
            "https://rss.donga.com/total.xml",
        ],
        # 글 스타일 힌트 (프롬프트에 전달)
        "style_hint": "건강/운동/식단",
        "style_desc": "건강, 운동, 식단, 다이어트, 영양, 피트니스 관련",
        "link_sources": [
            ("질병관리청", "https://www.kdca.go.kr"),
            ("국민건강보험공단", "https://www.nhis.or.kr"),
            ("식품의약품안전처", "https://www.mfds.go.kr"),
            ("대한의사협회", "https://www.kma.org"),
            ("서울대학교병원", "https://www.snuh.org"),
        ],
        # 커뮤니티 소스 (실제 경험담·토론글)
        "community_sources": [
            {"name": "클리앙 운동/스포츠",  "url": "https://www.clien.net/service/board/cm_sports", "type": "clien"},
            {"name": "클리앙 건강",          "url": "https://www.clien.net/service/board/cm_health", "type": "clien"},
            {"name": "뽐뿌 건강/다이어트",   "url": "https://www.ppomppu.co.kr/zboard.php?id=diet_health", "type": "ppomppu"},
        ],
    },

    "economy": {
        "name": "newbicon (경제/부동산/투자)",
        "display_name": "뉴비콘",
        # WordPress 연결
        "wp_url_env":  "WP2_URL",
        "wp_user_env": "WP2_USER",
        "wp_pass_env": "WP2_APP_PASSWORD",
        # 요일별 주제
        "topics": {
            0: "경제",
            1: "부동산",
            2: "투자",
            3: "경제",
            4: "부동산",
            5: "투자",
            6: "경제",
        },
        # RSS 피드 (경제/금융/부동산 특화)
        "rss_feeds": [
            "https://www.yna.co.kr/rss/economy.xml",       # 연합뉴스 경제
            "https://www.mk.co.kr/rss/30100041/",          # 매경 경제
            "https://rss.donga.com/economy.xml",           # 동아 경제
            "https://www.khan.co.kr/rss/rssdata/economy_news.xml",  # 경향 경제
            "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02",  # SBS 경제
        ],
        "style_hint": "경제/부동산/투자",
        "style_desc": "경제, 부동산, 주식, 투자, 금리, 재테크 관련",
        "link_sources": [
            ("한국은행", "https://www.bok.or.kr"),
            ("통계청", "https://www.kostat.go.kr"),
            ("금융감독원", "https://www.fss.or.kr"),
            ("국토교통부", "https://www.molit.go.kr"),
            ("KB부동산", "https://kbland.kr"),
            ("한국부동산원", "https://www.reb.or.kr"),
        ],
        # 커뮤니티 소스 (실제 경험담·토론글)
        "community_sources": [
            {"name": "클리앙 재테크",       "url": "https://www.clien.net/service/board/cm_stock",   "type": "clien"},
            {"name": "클리앙 부동산",       "url": "https://www.clien.net/service/board/cm_realty",  "type": "clien"},
            {"name": "뽐뿌 재테크",         "url": "https://www.ppomppu.co.kr/zboard.php?id=finance", "type": "ppomppu"},
        ],
    },
}


def get_site(site_key: str) -> dict:
    """사이트 설정 반환. 없으면 health 기본값."""
    if site_key not in SITES:
        print(f"  ⚠ 알 수 없는 사이트 키: {site_key} → health로 대체")
        return SITES["health"]
    return SITES[site_key]


def list_sites():
    """등록된 사이트 목록 출력"""
    for key, cfg in SITES.items():
        print(f"  --site {key:10s} → {cfg['name']}")
