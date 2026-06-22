"""
space.py - 뉴비콘 '우주 경제·투자' 포스팅

방향: 우주·방산 뉴스를 경제·산업 관점으로 심층 분석
- 단순 뉴스 번역·요약 금지
- 뉴스 사실 → 경제적 파급효과·시장 구조·투자 관점으로 풀어내는 글
- 종목 추천 금지 (예: "이 주식 사세요" 절대 금지)

요일별 앵글:
- 월 (글로벌 경제): 해외 우주 기업 계약·발사·합병 뉴스의 경제적 의미 분석
- 화 (국내 방산):   한국 방산·우주 산업 동향과 글로벌 시장 내 위치
- 수 (테크 트렌드): 우주 비즈니스·기술이 만드는 새 시장과 경쟁 구도
- 목 (기업 분석):   특정 우주 기업의 최근 행보가 산업 생태계에 미치는 영향
- 금 (주간 이슈):   한 주 우주 산업 핵심 이슈와 경제적 시사점 정리
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import random
import feedparser
import anthropic
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

from writer import parse_output, build_internal_links_prompt, build_seo_prompt
from wordpress import publish_post, fetch_recent_posts
from images import fetch_featured_image, fetch_multiple_images
from topic_tracker import get_recent_keywords, get_recent_titles, save_topic
from stocks import build_stock_section
from trending import fetch_all_trending, build_trending_section

# ★ newbicon 카테고리 ID — WordPress 관리자 → 카테고리에서 확인 후 입력
CATEGORY_ID = None

BLOG_NAME = '뉴비콘'

WP_ENV = {
    'wp_url_env':  'WP2_URL',
    'wp_user_env': 'WP2_USER',
    'wp_pass_env': 'WP2_APP_PASSWORD',
}

KST = timezone(timedelta(hours=9))

# ── 요일 배분 ─────────────────────────────────────────────
GLOBAL_DAYS  = {0}   # 월: 글로벌 우주 경제 뉴스 분석
KOREA_DAYS   = {1}   # 화: 국내 방산·우주 산업 분석
TECH_DAYS    = {2}   # 수: 우주 테크·비즈니스 트렌드
COMPANY_DAYS = {3}   # 목: 우주 기업 행보 & 산업 파급효과
WEEKLY_DAYS  = {4}   # 금: 주간 우주 경제 이슈 정리
SCIENCE_DAYS = {5}   # 토: 우주과학 탐구 (호기심·잡학)

DAY_NAMES = {0: '월요일', 1: '화요일', 2: '수요일', 3: '목요일', 4: '금요일', 5: '토요일'}

# ── RSS 피드 ──────────────────────────────────────────────
# 글로벌 우주 비즈니스·경제 중심
GLOBAL_FEEDS = [
    'https://spacenews.com/feed/',              # SpaceNews (계약·시장·정책)
    'https://www.nasaspaceflight.com/feed/',    # NASASpaceFlight (기술·발사)
    'https://spaceflightnow.com/feed/',         # Spaceflight Now (발사·계약)
    'https://www.parabolicarc.com/feed/',       # Parabolic Arc (상업우주)
    'https://www.teslarati.com/feed/',          # SpaceX 소식 포함
]

# 방산·항공우주 산업 중심
DEFENSE_FEEDS = [
    'https://breakingdefense.com/feed/',        # Breaking Defense (방산 업계)
    'https://www.defensenews.com/rss/',         # Defense News
    'https://spacenews.com/feed/',
    'https://aviationweek.com/rss',             # Aviation Week
    'https://www.nasaspaceflight.com/feed/',
]

# 국내 방산·우주 관련 (한국어 피드 + 글로벌 피드 혼용)
KOREA_FEEDS = [
    'https://www.hankyung.com/feed/all-news',   # 한국경제 (방산·항공우주 포함)
    'https://www.yna.co.kr/rss/all.xml',        # 연합뉴스
    'https://spacenews.com/feed/',              # 글로벌 기준 비교용
    'https://breakingdefense.com/feed/',
]


def _build_avoid_str(days: int = 60) -> str:
    keywords = get_recent_keywords(days=days, site='newbicon_space')
    titles   = get_recent_titles(days=days, site='newbicon_space')
    lines = []
    if keywords:
        lines.append('최근 키워드: ' + ', '.join(keywords[-30:]))
    if titles:
        lines.append('최근 제목 (의미상 비슷한 것 금지):')
        for t in titles[-20:]:
            lines.append(f'  - {t}')
    return '\n'.join(lines) if lines else '없음'


def _fetch_news(feeds: list, max_articles: int = 8) -> list[dict]:
    """RSS 피드에서 최신 뉴스 수집"""
    articles = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                title   = entry.get('title', '').strip()
                link    = entry.get('link', '').strip()
                summary = BeautifulSoup(
                    entry.get('summary', entry.get('description', '')),
                    'html.parser'
                ).get_text()[:500].strip()
                if title:
                    articles.append({
                        'title':  title,
                        'url':    link,
                        'summary': summary,
                        'source': feed.feed.get('title', feed_url),
                    })
                if len(articles) >= max_articles:
                    break
        except Exception as e:
            print(f"  ⚠ 뉴스 수집 실패 ({feed_url}): {e}")
        if len(articles) >= max_articles:
            break
    print(f"  뉴스 {len(articles)}건 수집")
    return articles


def _build_chat_instruction() -> str:
    if random.random() < 0.5:
        return f"""\
[대화 구간 - 어려운 개념 쉽게 풀기]
- 글 중간 내용이 복잡해지는 지점에서 아래 형식의 대화 블록을 정확히 1개 삽입한다.
- 대화는 3~5번 주고받는다.
- 말투: 친한 친구끼리 편하게 얘기하는 느낌. 짧고 자연스럽게.
  {BLOG_NAME}은 ~야/~거야/~잖아/~지/~어 같은 구어체.
  독자는 "정말?", "엥?", "그게 얼마나 큰 거야?", "그래서?" 같이 짧고 솔직하게.
  ❌ 금지: ~입니다, ~습니다, ~이다, ~한다 (딱딱한 말투 금지)
- 대화 중 핵심 단어·중요한 수치·핵심 문장에는 **굵게** 표시. 예: **1조 달러 시장**, **SpaceX 단독 수주**
[CHAT]
{BLOG_NAME}: (설명하는 말)
독자: (짧은 반응이나 질문)
{BLOG_NAME}: (이어지는 설명)
독자: (추가 반응)
{BLOG_NAME}: (마무리 설명)
[/CHAT]"""
    return "# [대화 구간 없음] 이 글은 대화 형식 없이 본문만으로 구성한다."


def _economy_format_rules() -> str:
    return f"""\
{build_seo_prompt()}

[모바일 최적화 — 가독성 필수 조건]
- 문단 길이: 2~3문장이면 반드시 줄 바꿈. 스마트폰 화면에서 한 문단이 5줄을 넘으면 안 된다.
- 문장 길이: 한 문장에 50자 이내. 길어지면 둘로 쪼갠다.
- 3개 이상 나열: 반드시 리스트(- ) 형식. 문장 안에 쉼표로 나열 금지.
- 수치·단계·비교: 표(Markdown `| 헤더 | 헤더 |` 형식) 또는 리스트(- ) 형식으로 시각화. 표는 자동으로 HTML 테이블로 변환된다.
- 굵게(**bold**)로 핵심 정보를 부각 — 스캐닝하는 독자가 굵은 글씨만 읽어도 핵심을 알 수 있어야 함.
- 텍스트 덩어리(벽돌 텍스트) 절대 금지. 줄 바꿈·리스트·대제목으로 여백을 만든다.

[형식 조건]
- 분량: 800단어 이상 (한국어 약 3200자 이상). 경제 분석글답게 충분한 깊이.
- 대제목(##): 반드시 **굵게(bold)**. 2~4개 중 매번 다르게.
- 소제목(###), 이모지, 리스트(-): 내용에 맞게 적절히.
- 굵게(**bold**): 기업명·수치·핵심 결론 문장에 1~2개/문단.
- 하이라이트(<mark>): 꼭 기억할 핵심 수치·결론 1~2곳.
- 수치는 반드시 비유로 스케일 체감: "수주액 1조 원" → "KAI 연간 매출의 30%에 해당"
- 전문용어 첫 등장 시 괄호로 쉬운 설명.
- 문체: 친근한 평어체. ~다/~이다/~한다. ❌ ~습니다/~요 금지.

[유머 - 1~2곳, 자연스럽게]
- 우주 스케일과 돈의 대비 개그("발사 한 번에 수백억인데 지연 보상은 0원이라는 거"),
  가벼운 자조 표현, 요즘 밈 뉘앙스. 억지 금지.

[외부 링크 - 본문에 반드시 2~3개 삽입]
형식: <a href="https://실제URL" target="_blank">앵커텍스트</a>
우선순위: 해당 기업 공식 IR·보도자료 > SpaceNews·Defense News 기사 > 한국경제·연합뉴스 기사 > 위키백과
주의: 홈페이지 루트 금지, 내용과 직접 관련된 하위 페이지·기사 URL만 사용. 확실한 URL만."""


def _meta_output_rules() -> str:
    return """\
---
글 본문이 끝나면 반드시 아래 6줄 출력. 절대 빠뜨리지 말 것.
FOCUS_KEYWORD: 핵심 검색어(2~4단어)
SEO_TITLE: SEO 제목(60자 이내, 포커스 키워드 앞쪽)
SEO_DESCRIPTION: 메타 설명(150~160자, 포커스 키워드 포함, 클릭 유도)
IMAGE_QUERY: 글 핵심 장면 영어 3~5단어 (로켓·위성·우주 산업 관련 구체적 장면)
  예) "rocket launch commercial space" / "satellite constellation orbit" / "defense aerospace contract"
TAGS: 태그1,태그2,태그3,태그4,태그5
TICKERS: 글에서 직접 언급한 상장 종목을 TradingView 형식으로. 없으면 없음.
  형식: EXCHANGE:SYMBOL (쉼표 구분, 최대 3개)
  예) NASDAQ:RKLB,TSX:MDA / KRX:010140,NYSE:BA / 없음"""


# ── 월: 글로벌 우주 경제 뉴스 분석 ──────────────────────────
def _post_global_economy(internal_links: str = ""):
    print("  🌍 글로벌 우주 경제 뉴스 수집 중...")
    news = _fetch_news(GLOBAL_FEEDS)
    avoid_str = _build_avoid_str()
    chat = _build_chat_instruction()
    trending_data = fetch_all_trending(days=7)
    trending_section = build_trending_section(trending_data)

    if not news:
        print("  ⚠ 뉴스 없음 → 트렌드 글로 대체")
        return _post_tech_trend()

    news_text = ''.join(
        f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"
        for i, n in enumerate(news, 1)
    )

    structures = [
        """\
1. 도입부 (3~4문장): 이 뉴스가 왜 우주 경제 측면에서 주목받는지.
2. ## **[무슨 계약·사건이 있었나]**: 핵심 사실. 금액·수량·기간 등 구체적 수치 필수.
3. ## **[이게 시장에 어떤 의미인가]**: 경쟁 구도 변화, 시장 점유율, 공급망 영향.
4. 마무리 (2~3문장): 이 흐름이 앞으로 어디로 향할지 한 줄 전망.""",

        """\
1. 도입부 (3~4문장): 숫자나 반전 사실로 시작 ("이 계약 규모가 ~에 맞먹는다" 등).
2. ## **[배경 — 왜 지금 이 뉴스가 나왔나]**: 업계 맥락, 경쟁사 동향, 정책 배경.
3. ## **[경제적 파급효과]**: 수주 기업의 매출 구조 변화, 경쟁사 영향, 공급망 재편.
4. ## **[투자자·산업 관계자가 봐야 할 포인트]**: 핵심 모니터링 지표, 리스크.
5. 마무리 (2문장): 짧고 임팩트 있게.""",

        """\
1. 도입부 (3~4문장): 이 사건이 '우주 경제'의 어떤 변곡점인지.
2. ## **[팩트 정리]**: 계약·발사·합병 등 핵심 사실을 수치 중심으로.
3. ## **[승자와 패자]**: 이 뉴스로 이득 보는 플레이어, 압박받는 플레이어.
4. ## **[한국 기업·투자자 관점]**: 국내 방산·우주 기업과의 연결고리.
5. ## **[앞으로의 변수]**: 이 흐름을 바꿀 수 있는 리스크·모니터링 포인트.
6. 마무리 (2문장): 짧게.""",
    ]

    prompt = f"""아래 최신 뉴스와 트렌딩 콘텐츠를 참고해 한국어 경제 분석 블로그 글을 써라.

---최신 뉴스 (참고용 — 직접 번역·복사 금지)---
{news_text}---

{trending_section}

[작성 원칙]
- 위 뉴스와 트렌딩 콘텐츠를 종합해 가장 경제적 파급효과가 크고 독자 관심이 높을 것 1개를 골라라.
- 이 뉴스의 사실 관계보다 **"이게 우주 산업 경제에 어떤 의미인지"**를 분석하는 글을 써라.
  예시 앵글: "로켓랩의 2분기 발사 성공률과 위성 수주 계약이 LEO 위성 경제에 미치는 파급효과"
- 계약 금액, 발사 횟수, 시장 점유율, 경쟁사 대비 수치를 반드시 포함한다.
- 단순 종목 추천("이 주식 사세요") 절대 금지. 산업·시장 구조 분석에 집중.
- 한국 독자 관점: 국내 방산/우주 기업(한화에어로스페이스, KAI, 한국항공우주연구원 등)과의
  연결고리가 있으면 자연스럽게 언급한다.

[금지 주제 - 최근 발행됨]
{avoid_str}

[제목 형식]
"~의 ~억 달러 계약이 의미하는 것", "~가 우주 시장을 바꾸는 방법",
"~의 경제적 파급효과" 등 경제 분석 느낌의 제목.

{_economy_format_rules()}

{chat}

[내용 구성 — 아래 중 하나 선택]
{random.choice(structures)}

{internal_links}

출처 표기 (글 맨 아래):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='글로벌경제')


# ── 화: 국내 방산·우주 산업 분석 ─────────────────────────────
def _post_korea_defense(internal_links: str = ""):
    print("  🇰🇷 국내 방산·우주 뉴스 수집 중...")
    news = _fetch_news(KOREA_FEEDS)
    avoid_str = _build_avoid_str()
    chat = _build_chat_instruction()
    trending_data = fetch_all_trending(days=7)
    trending_section = build_trending_section(trending_data)

    news_text = ''.join(
        f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"
        for i, n in enumerate(news, 1)
    ) if news else ""
    news_section = f"---참고 뉴스---\n{news_text}---" if news_text else \
        "# [뉴스 없음] 최근 국내 방산·우주 산업 주요 이슈를 자체 판단해서 작성."

    structures = [
        """\
1. 도입부 (3~4문장): 국내 방산·우주 산업이 왜 지금 주목받는지.
2. ## **[한국 방산·우주의 현재]**: 수주 규모, 주요 프로젝트, 글로벌 시장 내 위치.
3. ## **[경쟁국 대비 우리의 강점과 약점]**: 미국·유럽·이스라엘 등과의 비교.
4. 마무리 (2~3문장): 한국 방산·우주의 다음 과제.""",

        """\
1. 도입부 (3~4문장): 이번 뉴스가 국내 방산·우주 생태계에 갖는 의미.
2. ## **[핵심 사실 — 무슨 일이 있었나]**: 수주·개발·발사 등 구체적 수치 포함.
3. ## **[글로벌 공급망에서 한국의 포지션]**: 이 성과가 국제 경쟁에서 어떤 의미인지.
4. ## **[앞으로의 기회와 리스크]**: 다음 수주 기회, 기술 격차, 예산 변수.
5. 마무리 (2문장): 짧고 임팩트 있게.""",

        """\
1. 도입부 (3~4문장): 숫자로 시작 ("한국 방산 수출이 XX억 달러를 넘어섰다" 등).
2. ## **[한국이 잘하는 것]**: 강점 기술·제품·가격 경쟁력.
3. ## **[한국이 넘어야 할 것]**: 기술 격차, 신뢰도, 인증 장벽.
4. ## **[이번 뉴스의 경제적 파급효과]**: 관련 기업 수혜, 공급망 변화.
5. ## **[앞으로 3년 로드맵]**: 누리호 후속, KF-21 수출, 달 탐사 상업화.
6. 마무리 (2문장).""",
    ]

    prompt = f"""아래 뉴스와 트렌딩 콘텐츠를 참고해 국내 방산·우주 산업을 경제적 관점에서 분석하는 한국어 블로그 글을 써라.

{news_section}

{trending_section}

[작성 원칙]
- 위 뉴스와 트렌딩 콘텐츠를 종합해 독자 관심이 높은 국내 방산·우주 주제를 하나 선택하라.
- 한국 방산·우주 기업(한화에어로스페이스, KAI, LIG넥스원, 한국항공우주연구원, 쎄트렉아이 등)의
  최근 동향·수주·기술 개발을 경제 산업 관점으로 분석한다.
- "이 계약·기술이 한국 방산·우주 생태계와 글로벌 시장에 어떤 경제적 의미인지"를 핵심으로 써라.
- 글로벌 경쟁 구도(SpaceX, L3Harris, Airbus Defence 등)와의 비교를 자연스럽게 포함.
- 종목 추천 금지. 산업·시장 분석 중심.

[금지 주제 - 최근 발행됨]
{avoid_str}

[제목 형식]
"한국 방산이 ~를 해낸 진짜 이유", "누리호 이후 한국 우주 경제의 변화",
"K-방산이 ~억 달러 계약을 따낸 배경" 등 한국 방산·우주 경제 분석 느낌.

{_economy_format_rules()}

{chat}

[내용 구성]
{random.choice(structures)}

{internal_links}

출처 표기 (글 맨 아래):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='국내방산')


# ── 수: 우주 테크·비즈니스 트렌드 ───────────────────────────
def _post_tech_trend(internal_links: str = ""):
    print("  🚀 우주 테크·비즈니스 트렌드 뉴스 수집 중...")
    news = _fetch_news(GLOBAL_FEEDS)
    avoid_str = _build_avoid_str()
    chat = _build_chat_instruction()
    trending_data = fetch_all_trending(days=7)
    trending_section = build_trending_section(trending_data)

    news_text = ''.join(
        f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"
        for i, n in enumerate(news, 1)
    ) if news else ""
    news_section = f"---참고 뉴스---\n{news_text}---" if news_text else \
        "# [뉴스 없음] 최근 우주 테크·비즈니스 트렌드를 자체 판단해서 작성."

    structures = [
        """\
1. 도입부 (3~4문장): 이 기술·트렌드가 왜 지금 우주 산업 경제를 바꾸고 있는지.
2. ## **[이 트렌드의 핵심]**: 어떤 기술·비즈니스 모델이 부상하고 있는지.
3. ## **[시장 규모와 플레이어 경쟁]**: 누가 선두이고, 어디서 돈이 만들어지는지.
4. 마무리 (2~3문장): 이 트렌드가 5년 뒤 어디까지 갈지.""",

        """\
1. 도입부 (3~4문장): 우주 비즈니스의 특정 변화를 숫자로 보여주며 시작.
2. ## **[새로운 비즈니스 모델]**: 기존 우주 산업과 어떻게 다른지, 왜 돈이 되는지.
3. ## **[주요 기업과 경쟁 구도]**: 선두주자, 추격자, 니치 플레이어.
4. ## **[한국에 오는 기회와 위협]**: 국내 기업·투자자 관점의 시사점.
5. 마무리 (2문장): 짧게.""",

        """\
1. 도입부 (3~4문장): "~년 전만 해도 불가능했던 일이 지금은..." 식의 변화 대비로 시작.
2. ## **[기술이 열어준 새 시장]**: 재사용 로켓, LEO 위성망, 달 경제 등 구체적 시장 규모.
3. ## **[돈의 흐름]**: 누가 투자하고, 어디서 수익이 나고, 어떤 수익 모델인지.
4. ## **[리스크와 불확실성]**: 규제, 기술 장벽, 경쟁 과열 가능성.
5. ## **[앞으로 주목할 변수]**: 핵심 모니터링 포인트 3가지.
6. 마무리 (2문장): 짧고 강렬하게.""",
    ]

    prompt = f"""아래 뉴스와 트렌딩 콘텐츠를 참고해 우주 테크·비즈니스 트렌드를 경제적 관점으로 분석하는 한국어 블로그 글을 써라.

{news_section}

{trending_section}

[작성 원칙]
- 위 뉴스와 트렌딩 콘텐츠를 종합해 독자 관심이 가장 높은 우주 테크·비즈니스 트렌드 하나를 선택하라.
- 재사용 로켓, LEO 메가 위성망, 우주 인터넷, 달 경제, 우주 제조·관광 등
  우주 비즈니스의 새로운 트렌드를 경제·산업 구조 관점에서 분석한다.
- "이 트렌드가 시장을 어떻게 바꾸고 어디서 돈이 만들어지는지"를 중심으로.
- 시장 규모(달러), 성장률, 주요 플레이어 점유율 같은 수치를 최대한 포함.
- 종목 추천 금지. 비즈니스·산업 구조 분석 중심.

[금지 주제 - 최근 발행됨]
{avoid_str}

[제목 형식]
"~가 돈이 되는 진짜 이유", "~조 달러 시장이 열린다", "우주 경제의 다음 판은 ~다"
등 비즈니스·경제 트렌드 분석 느낌의 제목.

{_economy_format_rules()}

{chat}

[내용 구성]
{random.choice(structures)}

{internal_links}

출처 표기 (글 맨 아래):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='테크트렌드')


# ── 목: 우주 기업 행보 & 산업 파급효과 ──────────────────────
def _post_company_analysis(internal_links: str = ""):
    print("  🏢 우주 기업 뉴스 수집 중...")
    news = _fetch_news(DEFENSE_FEEDS + GLOBAL_FEEDS)
    avoid_str = _build_avoid_str()
    chat = _build_chat_instruction()
    trending_data = fetch_all_trending(days=7)
    trending_section = build_trending_section(trending_data)

    if not news:
        return _post_global_economy()

    news_text = ''.join(
        f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"
        for i, n in enumerate(news, 1)
    )

    structures = [
        """\
1. 도입부 (3~4문장): 이 기업의 최근 행보가 왜 업계 전체에 신호가 되는지.
2. ## **[이번에 무슨 일을 했나]**: 계약·발사·합병·기술 발표 등 핵심 사실.
3. ## **[경쟁 생태계에 미치는 영향]**: 경쟁사, 파트너사, 고객사 관점의 변화.
4. 마무리 (2~3문장): 이 기업의 다음 행보와 산업 전망.""",

        """\
1. 도입부 (3~4문장): 이 기업의 행보를 숫자로 시작 ("이 계약 하나로 매출이 X% 늘었다" 등).
2. ## **[기업의 전략적 선택]**: 왜 이 시점에 이 결정을 했는지 배경 분석.
3. ## **[산업 생태계 파급효과]**: 공급망, 경쟁 구도, 가격 시장에 미치는 영향.
4. ## **[리스크와 기회]**: 이 전략이 성공하려면 뭐가 필요하고, 실패 변수는 무엇인가.
5. 마무리 (2문장): 짧게.""",

        """\
1. 도입부 (3~4문장): 이 기업이 우주 경제에서 차지하는 위치부터.
2. ## **[최근 행보 팩트]**: 계약·수주·기술 발표·파트너십 등 구체적 수치.
3. ## **[이게 경쟁사에 주는 압박]**: 동종 업계 경쟁 구도 변화.
4. ## **[공급망·파트너십 재편]**: 이 기업과 일하는 협력사, 고객사에 미치는 영향.
5. ## **[투자·산업 관점에서 봐야 할 것]**: 핵심 지표, 다음 모니터링 포인트.
6. 마무리 (2문장).""",
    ]

    prompt = f"""아래 우주·방산 기업 뉴스와 트렌딩 콘텐츠를 바탕으로 기업 행보의 산업 파급효과를 분석하는 한국어 블로그 글을 써라.

---최신 뉴스 (참고용 — 직접 번역·복사 금지)---
{news_text}---

{trending_section}

[작성 원칙]
- 위 뉴스와 트렌딩 콘텐츠를 종합해 독자 관심이 가장 높고 파급효과가 큰 기업 1곳의 행보를 골라 중심 주제로 삼아라.
  SpaceX, Rocket Lab, Blue Origin, Boeing, Northrop Grumman, L3Harris, Airbus Defence,
  Hanwha Aerospace, KAI 등 우주·방산 기업 모두 대상.
- "이 기업의 X 결정이 Y 산업 생태계에 어떤 경제적 파급효과를 주는가"를 분석하는 글.
- 구체적 수치(계약 금액, 발사 횟수, 시장 점유율, 매출 비중)를 반드시 포함.
- 종목 추천 금지. 기업 전략·산업 구조 분석 중심.

[금지 주제 - 최근 발행됨]
{avoid_str}

[제목 형식]
"~의 ~억 달러 계약이 우주 산업을 바꾸는 이유",
"~가 이 결정을 내린 진짜 배경", "~의 행보가 경쟁사에 주는 경고"
등 기업 분석 느낌의 제목.

{_economy_format_rules()}

{chat}

[내용 구성]
{random.choice(structures)}

{internal_links}

출처 표기 (글 맨 아래):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='기업분석')


# ── 금: 주간 우주 경제 이슈 정리 ────────────────────────────
def _post_weekly_issue(internal_links: str = ""):
    print("  📋 주간 우주 경제 이슈 뉴스 수집 중...")
    news = _fetch_news(GLOBAL_FEEDS + DEFENSE_FEEDS, max_articles=10)
    avoid_str = _build_avoid_str()
    chat = _build_chat_instruction()
    trending_data = fetch_all_trending(days=7)
    trending_section = build_trending_section(trending_data)

    news_text = ''.join(
        f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"
        for i, n in enumerate(news, 1)
    ) if news else ""
    news_section = f"---이번 주 주요 뉴스---\n{news_text}---" if news_text else \
        "# [뉴스 없음] 이번 주 우주 경제 주요 이슈를 자체 판단해서 작성."

    structures = [
        """\
1. 도입부 (3~4문장): 이번 주 우주 산업을 한 줄로 요약하며 시작.
2. ## **[이번 주 핵심 이슈]**: 가장 파급효과가 큰 뉴스 1~2개를 경제적 관점으로 분석.
3. ## **[업계 흐름 & 경쟁 구도 변화]**: 이번 주 뉴스들이 만드는 트렌드.
4. 마무리 (2~3문장): 다음 주 주목할 이벤트·변수.""",

        """\
1. 도입부 (3~4문장): "이번 주 우주 산업에서 놓치면 안 될 것들" 식으로 시작.
2. ## **[Big Deal — 이번 주 가장 큰 계약·사건]**: 경제적 파급효과 중심 분석.
3. ## **[기술 & 발사 이슈]**: 기술 발표·발사 성공·실패가 시장에 주는 신호.
4. ## **[한국이 주목해야 할 포인트]**: 국내 방산·우주 관점의 시사점.
5. 마무리 (2문장): 짧게.""",
    ]

    prompt = f"""아래 이번 주 우주·방산 뉴스와 트렌딩 콘텐츠를 바탕으로 주간 우주 경제 이슈를 분석하는 한국어 블로그 글을 써라.

{news_section}

{trending_section}

[작성 원칙]
- 위 뉴스와 트렌딩 콘텐츠를 종합해 이번 주 가장 주목받은 이슈 2~3개를 엮어서 분석한다.
- 단순 뉴스 나열이 아니라 "이 이슈들이 우주 경제의 어떤 흐름을 보여주는가"를 연결해서 써라.
- 구체적 수치(금액, 계약 기간, 위성 수, 발사 성공률 등) 반드시 포함.
- 종목 추천 금지. 산업 트렌드·경제 구조 분석 중심.

[금지 주제 - 최근 발행됨]
{avoid_str}

[제목 형식]
"이번 주 우주 경제 핵심 정리", "우주 산업이 보낸 이번 주 신호들",
"~주차 우주 비즈니스 이슈" 등 주간 정리 느낌의 제목.

{_economy_format_rules()}

{chat}

[내용 구성]
{random.choice(structures)}

{internal_links}

출처 표기 (글 맨 아래):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='주간이슈')


# ── 토: 우주과학 탐구 (호기심·잡학) ─────────────────────────
def _post_space_science(internal_links: str = ""):
    """토요일 — 우주과학 호기심·잡학 글 (경제 분석 없이 순수 우주 이야기)"""
    print("  🔭 우주과학 탐구 글 작성 중...")
    avoid_str = _build_avoid_str()
    chat = _build_chat_instruction()

    intro_styles = [
        '1인칭 경험담으로 시작 ("어릴 때 밤하늘을 보다가", "뉴스에서 봤는데", "문득 궁금해졌다" 등)',
        '독자에게 직접 질문 던지기 ("밤하늘 올려다본 게 언제야?", "이 숫자 보면 실감이 안 될 거다" 등)',
        '의외의 사실·반전으로 시작 ("사실 이거 아는 사람 드물어", "교과서에서 배운 것과 달랐다" 등)',
        '스케일 대비로 시작 ("지구가 얼마나 작은지 알면 허무해진다", "우주의 나이를 1년으로 줄이면" 등)',
    ]
    intro_style = random.choice(intro_styles)

    structures = [
        f"""\
1. 도입부 (3~4문장): {intro_style}
2. ## **[핵심 개념 / 왜 그런지]**: 과학적 사실을 비유·예시로 쉽게 풀기. 충분히 길게.
3. ## **[더 깊이 파고들면]**: 연관 흥미 사실, 최신 발견, 의외의 연결고리.
4. 마무리 (2~3문장): 스케일감 있는 한 줄 정리 + 여운.""",

        f"""\
1. 도입부 (3~4문장): {intro_style}
2. ## **[흔한 오해 / 잘못 알고 있는 것]**: 대부분 이렇게 알고 있는데 사실은 다르다.
3. ## **[진짜 과학적 사실]**: 구체적 수치·근거·최신 연구 포함. 비유로 쉽게.
4. ## **[우리 일상과의 연결]**: 이 우주 현상이 지구/일상과 어떻게 이어지는지.
5. 마무리 (2문장): 짧고 여운 있게.""",

        f"""\
1. 도입부 (3~4문장): {intro_style}
2. ## **[우주의 스케일 / 배경]**: 이 주제가 얼마나 거대하고 경이로운지 맥락 설명.
3. ## **[핵심 과학 원리]**: 단계적으로 쉽게. 비유와 구체적 숫자 필수.
4. ## **[인류가 알아낸 것들]**: 탐사·관측 역사, 최신 발견, 앞으로의 과제.
5. 마무리 (2~3문장): 우주적 관점에서의 한 줄 결론.""",
    ]

    prompt = f"""토요일 독자를 위한 우주과학 탐구 블로그 글을 써라.

[주제 선택]
우주·천문학·행성·별·은하·블랙홀·탐사선·우주론·물리법칙 등 우주과학 전반에서 하나를 골라라.
"블랙홀에 빨려 들어가면 어떻게 될까?", "달은 왜 지구 주위를 돌까?",
"태양이 사라지면 지구는 8분 후에야 알 수 있다", "우주는 계속 팽창 중이다" 처럼
규모가 크고 상상력을 자극하거나, 알고 나면 세계관이 흔들리는 주제로.
전공자가 아닌 일반인도 술술 읽힐 수 있도록 쉽게 써라.
경제·투자·산업 분석 없이, 순수하게 우주의 신비와 과학적 원리를 탐구하는 글.

[금지 주제 - 최근 발행됨, 의미상 비슷한 것도 피할 것]
{avoid_str}

[제목 형식]
"~하면 어떻게 될까?", "사실 ~였다", "~의 진짜 크기", "우주에서 ~가 가능할까?" 등
호기심·스케일 자극 형식.

{build_seo_prompt()}

[모바일 최적화 — 가독성 필수 조건]
- 문단 길이: 2~3문장이면 반드시 줄 바꿈. 스마트폰 화면에서 한 문단이 5줄을 넘으면 안 된다.
- 문장 길이: 한 문장에 50자 이내. 길어지면 둘로 쪼갠다.
- 3개 이상 나열: 반드시 리스트(- ) 형식. 문장 안에 쉼표로 나열 금지.
- 굵게(**bold**)로 핵심 정보를 부각 — 스캐닝하는 독자가 굵은 글씨만 읽어도 핵심을 알 수 있어야 함.
- 텍스트 덩어리(벽돌 텍스트) 절대 금지. 줄 바꿈·리스트·대제목으로 여백을 만든다.

[형식 조건]
- 분량: 700단어 이상 (한국어 약 2800자 이상).
- 대제목(##): 반드시 **굵게(bold)**. 2~4개 중 매번 다르게.
- 소제목(###), 이모지, 리스트(-): 내용에 맞게 적절히.
- 굵게(**bold**): 핵심 키워드·수치·결론 문장에 1~2개/문단.
- 하이라이트(<mark>): 꼭 기억할 핵심 문구 1~2곳.
- 수치는 반드시 일상 비유로 체감: "1광년" → "자동차로 달리면 1억 년"
- 전문용어 첫 등장 시 괄호로 쉬운 설명.
- 문체: 친근한 평어체. ~다/~이다. ❌ ~습니다/~요 금지.

[유머 - 1~2곳, 자연스럽게]
우주 스케일과 일상의 대비 개그, 가벼운 말장난, 요즘 밈 뉘앙스. 억지 금지.

[외부 링크 - 본문에 반드시 2~3개]
NASA, ESA, Space.com, Universe Today, 한국천문연구원, 한국어 위키백과 등.
홈페이지 루트 금지, 내용과 직접 관련된 하위 페이지 URL만.

{chat}

[내용 구성]
{random.choice(structures)}

{internal_links}

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='우주과학')


# ── 공통 실행·발행 ─────────────────────────────────────────
def _run_and_publish(prompt: str, mode: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    print(f"  Claude API 호출 중 ({mode})...")
    msg = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8096,
        messages=[{'role': 'user', 'content': prompt}],
    )
    raw = msg.content[0].text
    result = parse_output(raw, blog_name=BLOG_NAME)

    print(f"  제목: {result['title']}")
    print(f"  본문: {len(result['content_markdown'])}자")
    print(f"  포커스 키워드: {result.get('focus_keyword', '-')}")

    image_query = result.get('image_query', 'rocket launch commercial space industry')
    print(f"  이미지 검색: {image_query}")
    featured_image = fetch_featured_image(image_query, nasa=True)
    body_images    = fetch_multiple_images(image_query, count=3, nasa=True)

    if featured_image:
        print(f"  대표 이미지: {featured_image['credit']}")
    if body_images:
        print(f"  본문 이미지: {len(body_images)}장")

    # 종목 차트 + AI 분석 섹션 (경제 포스트에만)
    tickers = result.get('tickers', [])
    content_html = result['content_html']
    if tickers:
        stock_section = build_stock_section(
            tickers_raw=tickers,
            post_excerpt=result['content_markdown'][:1500],
            client=client,
        )
        if stock_section:
            content_html = content_html + "\n\n" + stock_section

    post_result = publish_post(
        title=result['title'],
        content_html=content_html,
        excerpt=result.get('excerpt', ''),
        tags=result['tags'],
        category_id=CATEGORY_ID,
        status='draft',
        featured_image_url=featured_image['url'] if featured_image else None,
        image_list=body_images,
        focus_keyword=result.get('focus_keyword', ''),
        seo_title=result.get('seo_title', ''),
        seo_description=result.get('seo_description', ''),
        image_alt=result.get('focus_keyword', result['title']),
        wp_env=WP_ENV,
    )

    save_topic(
        keyword=result.get('focus_keyword', result['title']),
        title=result['title'],
        topic=f'우주경제({mode})',
        site='newbicon_space',
    )

    print(f"  ✅ ({mode}) 임시글 저장 완료! ID: {post_result['id']} / {post_result['url']}")
    return post_result


# ── 진입점 ────────────────────────────────────────────────
def post_space():
    weekday = datetime.now(KST).weekday()
    day = DAY_NAMES.get(weekday, '')

    print("  🔗 내부 링크용 최근 발행글 조회 중...")
    recent_posts = fetch_recent_posts(WP_ENV, count=8)
    internal_links = build_internal_links_prompt(recent_posts)
    if recent_posts:
        print(f"    발행글 {len(recent_posts)}건 확인")

    if weekday in GLOBAL_DAYS:
        print(f"  🌍 오늘은 {day} → 글로벌 우주 경제 뉴스 분석")
        return _post_global_economy(internal_links)
    elif weekday in KOREA_DAYS:
        print(f"  🇰🇷 오늘은 {day} → 국내 방산·우주 산업 분석")
        return _post_korea_defense(internal_links)
    elif weekday in TECH_DAYS:
        print(f"  🚀 오늘은 {day} → 우주 테크·비즈니스 트렌드")
        return _post_tech_trend(internal_links)
    elif weekday in COMPANY_DAYS:
        print(f"  🏢 오늘은 {day} → 우주 기업 행보 & 산업 파급효과")
        return _post_company_analysis(internal_links)
    elif weekday in WEEKLY_DAYS:
        print(f"  📋 오늘은 {day} → 주간 우주 경제 이슈 정리")
        return _post_weekly_issue(internal_links)
    else:  # SCIENCE_DAYS (토)
        print(f"  🔭 오늘은 {day} → 우주과학 탐구")
        return _post_space_science(internal_links)


if __name__ == '__main__':
    post_space()
