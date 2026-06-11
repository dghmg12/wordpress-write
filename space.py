"""
space.py - '우주과학/AI' 카테고리 뉴비콘 포스팅

- 월 (우주 뉴스):    최신 우주과학 뉴스 기반 글
- 화 (우주 잡학):    우주과학 호기심/잡학 글
- 수 (우주산업):     우주산업·우주경제·민간우주 트렌드 글
- 목 (AI×우주 뉴스):  우주 탐사·천문학에 AI·반도체가 쓰이는 최신 뉴스 글
- 금 (AI×우주 트렌드): 우주 기술과 AI·반도체의 교차점 심층 트렌드 글
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

from writer import parse_output
from wordpress import publish_post
from images import fetch_featured_image, fetch_multiple_images
from topic_tracker import get_recent_keywords, get_recent_titles, save_topic

# ★ newbicon '우주과학' 카테고리 ID — WordPress 관리자 → 카테고리에서 확인 후 입력
CATEGORY_ID = None

BLOG_NAME = '뉴비콘'


def _build_avoid_str(days: int = 60) -> str:
    """최근 발행된 키워드+제목을 함께 반환해 중복 방지"""
    keywords = get_recent_keywords(days=days, site='newbicon_space')
    titles   = get_recent_titles(days=days, site='newbicon_space')
    lines = []
    if keywords:
        lines.append('최근 키워드: ' + ', '.join(keywords[-30:]))
    if titles:
        lines.append('최근 제목 (이 주제들과 겹치거나 의미상 비슷한 것 금지):')
        for t in titles[-20:]:
            lines.append(f'  - {t}')
    return '\n'.join(lines) if lines else '없음'

WP_ENV = {
    'wp_url_env':  'WP2_URL',
    'wp_user_env': 'WP2_USER',
    'wp_pass_env': 'WP2_APP_PASSWORD',
}

KST = timezone(timedelta(hours=9))

# 우주 뉴스 RSS 피드
SPACE_NEWS_FEEDS = [
    'https://www.nasa.gov/feed/',                    # NASA 공식
    'https://spacenews.com/feed/',                   # SpaceNews
    'https://www.space.com/feeds/all',               # Space.com
    'https://www.universetoday.com/feed/',           # Universe Today
    'https://skyandtelescope.org/feed/',             # Sky & Telescope
]

# 요일별 타입 (0=월 ... 4=금)
NEWS_DAYS      = {0}   # 월: 우주 최신 뉴스
TRIVIA_DAYS    = {1}   # 화: 우주 잡학
INDUSTRY_DAYS  = {2}   # 수: 우주산업
AI_NEWS_DAYS   = {3}   # 목: AI/반도체 뉴스
AI_TREND_DAYS  = {4}   # 금: AI/반도체 트렌드


def _fetch_space_news(max_articles: int = 6) -> list[dict]:
    """우주 뉴스 RSS 수집"""
    articles = []
    for feed_url in SPACE_NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                title   = entry.get('title', '').strip()
                link    = entry.get('link', '').strip()
                summary = BeautifulSoup(
                    entry.get('summary', entry.get('description', '')),
                    'html.parser'
                ).get_text()[:400].strip()
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
            print(f"  ⚠ 우주 뉴스 수집 실패 ({feed_url}): {e}")
        if len(articles) >= max_articles:
            break
    print(f"  우주 뉴스 {len(articles)}건 수집")
    return articles


def _build_chat_instruction() -> str:
    """대화 구간 지시문 (50% 확률)"""
    if random.random() < 0.5:
        return f"""\
[대화 구간 - 어려운 내용 쉽게 풀기]
- 글 중간 내용이 어려워지는 지점에서 아래 형식의 대화 블록을 정확히 1개 삽입한다.
- 대화는 3~5번 주고받는다.
- 말투: 친한 친구끼리 편하게 얘기하는 느낌. 짧고 자연스럽게.
  {BLOG_NAME}은 ~야/~거야/~잖아/~지/~어 같은 구어체 사용.
  독자는 "정말?", "엥?", "그게 얼마나 큰 거야?", "그래서?" 같이 짧고 솔직하게.
  ✅ 올바른 예:
    {BLOG_NAME}: 빛이 1초에 지구를 7바퀴 반을 도는 거거든.
    독자: 엥, 그게 가능해?
    {BLOG_NAME}: 그러니까 태양 빛이 여기 닿는 데 8분이나 걸리는 거지.
  ❌ 금지: ~입니다, ~습니다, ~이다, ~한다 (딱딱한 말투 금지)
- 출력 형식 (반드시 이 대로):
[CHAT]
{BLOG_NAME}: (설명하는 말)
독자: (짧은 반응이나 질문)
{BLOG_NAME}: (이어지는 설명)
독자: (추가 반응)
{BLOG_NAME}: (마무리 설명)
[/CHAT]"""
    return "# [대화 구간 없음] 이 글은 대화 형식 없이 본문만으로 구성한다."


def _common_format_rules() -> str:
    return """\
[형식 조건]
- 분량: 700단어 이상 (한국어 약 2800자 이상). 할 말 있어서 길어지는 글. 억지 패딩 금지.
- 대제목(##): 반드시 **굵게(bold)**. 2개·3개·4개 중 하나를 매번 다르게 선택해서 사용한다.
- 소제목(###), 이모지, 리스트(-): 내용에 맞게 적절히.
- 굵게(**bold**): 핵심 키워드·수치·결론 문장에 1~2개/문단.
- 하이라이트(<mark>): 꼭 기억할 핵심 문구 1~2곳.
- 수치·거리·시간은 반드시 일상 비유로 스케일을 체감시켜라.
  예) "1광년" → "자동차로 달리면 1억 년", "태양 질량의 10억 배" → "지구를 100만 개 넣어도 남는 크기"
- 전문용어 첫 등장 시 괄호로 쉬운 설명 추가.
- 문체: 친근한 평어체. ~다/~이다/~한다. ❌ ~습니다/~요/~죠 금지.
- 각 문단: 할 말 있으면 길게, 없으면 짧게.

[유머 - 글 전체에 1~2곳, 자연스럽게]
- 억지로 넣지 않는다. 맥락이 맞을 때만. 없으면 안 넣어도 된다.
- 허용되는 유머: 우주 스케일과 일상의 대비를 이용한 개그("지구가 모래알이라면... 근데 모래알도 너무 크다"),
  가벼운 말장난·언어유희, 공감되는 자조적 표현("이거 나만 몰랐나?", "알고 나니 더 허무하다"),
  요즘 밈 뉘앙스("이거 실화임?", "소름 돋았으면 손 들어", "~각이다").
- 금지: 특정 집단·인물 비하, 억지 개그, 콘텐츠 흐름을 끊는 유머.
- 유머 위치: 도입부 첫 문장, 대화 구간, 마무리 중 자연스러운 곳 1~2군데면 충분하다.

[외부 링크 - 본문에 반드시 2~3개 삽입]
형식: <a href="https://실제URL" target="_blank">앵커텍스트</a>
신뢰도 순서: NASA·ESA 등 우주기관 공식 > 대형 언론사 > 유명 과학 사이트 > 위키백과
추천 소스 (주제에 맞게 선택):
- NASA 공식 (nasa.gov): 탐사선·행성·임무 관련 하위 페이지
- ESA (esa.int): 유럽우주국 탐사·관측 관련
- Space.com / Universe Today: 관련 기사 페이지
- SpaceNews (spacenews.com): 우주산업·정책 관련
- Hubble / Webb (hubblesite.org / webbtelescope.org): 망원경 관련
- 한국천문연구원 (kasi.re.kr): 국내 독자 친화적
- 한국어 위키백과 (ko.wikipedia.org): 개념 설명 용어에
- 조선·중앙·한국경제 등 국내 대형 언론사 우주 관련 기사
주의:
  ✅ 홈페이지 루트 금지 — 내용과 직접 관련된 하위 페이지·기사 URL만 사용
  ✅ 앵커텍스트는 자연스러운 한국어 문구로 ("NASA 화성 탐사 미션 소개" 등)
  ❌ 존재하지 않을 것 같은 URL 지어내지 말 것 — 확실한 URL만 사용"""


def _meta_output_rules() -> str:
    return """\
---
글 본문이 끝나면 반드시 아래 5줄 출력. 절대 빠뜨리지 말 것.
FOCUS_KEYWORD: 핵심 검색어(2~4단어)
SEO_TITLE: SEO 제목(60자 이내, 포커스 키워드 앞쪽)
SEO_DESCRIPTION: 메타 설명(150~160자, 포커스 키워드 포함, 클릭 유도)
IMAGE_QUERY: 글 핵심 장면 영어 3~5단어 (구체적 사물/장면, 추상어 금지)
  예) 블랙홀 → "black hole space galaxy swirling"
      달 탐사 → "moon surface astronaut NASA lunar"
      화성 탐사 → "Mars rover red planet surface NASA"
TAGS: 태그1,태그2,태그3,태그4,태그5"""


# ── 뉴스 기반 글 ──────────────────────────────────────────
def _post_space_news():
    """최신 우주 뉴스를 바탕으로 한국어 블로그 글 작성"""
    print("  📡 우주 최신 뉴스 수집 중...")
    news = _fetch_space_news()

    if not news:
        print("  ⚠ 뉴스 수집 실패 → 잡학 글로 대체")
        return _post_space_trivia()

    news_text = ""
    for i, n in enumerate(news, 1):
        news_text += f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"

    avoid_str = _build_avoid_str(days=60)
    chat_instruction = _build_chat_instruction()

    prompt = f"""아래 최신 우주 뉴스들을 참고해서 한국어 블로그 글을 써라.

---최신 우주 뉴스 (참고용 — 직접 번역·복사 금지)---
{news_text}
---

[작성 원칙]
- 뉴스 중 가장 흥미롭고 임팩트 있는 것 1개를 골라 중심 주제로 삼아라.
- 뉴스를 그대로 번역하거나 요약하지 않는다. 독자에게 "이게 왜 대단한지", "이게 우리에게 무슨 의미인지"를 설명하는 내 글을 쓴다.
- 전문용어는 반드시 쉬운 말로 풀어서 설명한다.
- 읽고 나서 "오, 우주에서 이런 일이 있었구나!" 반응이 나오게.

[금지 주제 - 최근 사용됨]
{avoid_str}

[제목 형식]
"~가 발견됐다", "NASA가 공개한 ~", "드디어 밝혀진 ~" 등 뉴스 느낌이 나는 제목.
단, 낚시성 제목 금지 — 본문 내용과 일치해야 한다.

{_common_format_rules()}

[내용 구성 — 아래 중 하나를 랜덤 선택]
패턴1 (H2 2개):
1. 도입부 (3~4문장): 이 뉴스가 왜 주목받는지.
2. ## **[무슨 일이 있었나]**: 핵심 사실 쉽게 설명. 수치·비유 필수.
3. ## **[이게 왜 중요한가]**: 과학적·인류적 의미.
4. 마무리 (2~3문장): 우주적 관점의 여운.

패턴2 (H2 3개):
1. 도입부 (3~4문장): 이 뉴스가 왜 주목받는지.
2. ## **[무슨 일이 있었나]**: 핵심 사실 쉽게 설명.
3. ## **[이게 왜 중요한가]**: 과학적·인류적 의미.
4. ## **[앞으로 어떻게 될까]**: 후속 전망, 탐사 계획, 남은 질문.
5. 마무리 (2~3문장): 우주적 관점의 여운.

패턴3 (H2 4개):
1. 도입부 (3~4문장): 이 뉴스가 왜 주목받는지.
2. ## **[배경 — 여기까지 어떻게 왔나]**: 이 발견·사건의 역사적 맥락.
3. ## **[무슨 일이 있었나]**: 핵심 사실 쉽게 설명. 수치·비유 필수.
4. ## **[이게 왜 중요한가]**: 과학적·인류적 의미.
5. ## **[앞으로 어떻게 될까]**: 후속 전망과 남은 질문.
6. 마무리 (2문장): 짧고 강렬하게.

출처 표기 (글 맨 아래):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_chat_instruction_placeholder(chat_instruction)}

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='뉴스')


def _chat_instruction_placeholder(chat_instruction: str) -> str:
    return chat_instruction


# 우주×AI·반도체 관련 뉴스 RSS (우주 기술·탐사에 AI/반도체가 활용되는 내용 포함)
AI_NEWS_FEEDS = [
    'https://www.nasa.gov/feed/',                    # NASA — AI 활용 탐사 미션 포함
    'https://spacenews.com/feed/',                   # SpaceNews — 위성·탐사 기술 전반
    'https://www.universetoday.com/feed/',           # Universe Today — 천문 AI 연구 포함
    'https://www.technologyreview.com/feed/',        # MIT Tech Review — 우주×AI 교차점
    'https://spectrum.ieee.org/feeds/topic/aerospace.rss',  # IEEE Aerospace
]

AI_TREND_FEEDS = [
    'https://spacenews.com/feed/',
    'https://www.nasaspaceflight.com/feed/',
    'https://www.technologyreview.com/feed/',
    'https://spectrum.ieee.org/feeds/topic/aerospace.rss',
    'https://skyandtelescope.org/feed/',
]

# 우주산업 뉴스 RSS
SPACE_INDUSTRY_FEEDS = [
    'https://spacenews.com/feed/',                        # SpaceNews (산업 비중 높음)
    'https://www.nasaspaceflight.com/feed/',              # NASASpaceFlight
    'https://www.parabolicarc.com/feed/',                 # Parabolic Arc (상업우주)
    'https://spaceflightnow.com/feed/',                   # Spaceflight Now
    'https://www.teslarati.com/feed/',                    # SpaceX 소식 포함
]


def _fetch_industry_news(max_articles: int = 6) -> list[dict]:
    """우주산업 뉴스 RSS 수집"""
    articles = []
    for feed_url in SPACE_INDUSTRY_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                title   = entry.get('title', '').strip()
                link    = entry.get('link', '').strip()
                summary = BeautifulSoup(
                    entry.get('summary', entry.get('description', '')),
                    'html.parser'
                ).get_text()[:400].strip()
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
            print(f"  ⚠ 우주산업 뉴스 수집 실패 ({feed_url}): {e}")
        if len(articles) >= max_articles:
            break
    print(f"  우주산업 뉴스 {len(articles)}건 수집")
    return articles


def _fetch_ai_news(feeds: list, max_articles: int = 6) -> list[dict]:
    """AI·반도체 뉴스 RSS 수집"""
    articles = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                title   = entry.get('title', '').strip()
                link    = entry.get('link', '').strip()
                summary = BeautifulSoup(
                    entry.get('summary', entry.get('description', '')),
                    'html.parser'
                ).get_text()[:400].strip()
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
            print(f"  ⚠ AI 뉴스 수집 실패 ({feed_url}): {e}")
        if len(articles) >= max_articles:
            break
    print(f"  AI/반도체 뉴스 {len(articles)}건 수집")
    return articles


def _ai_format_rules() -> str:
    return """\
[형식 조건]
- 분량: 700단어 이상 (한국어 약 2800자 이상). 할 말 있어서 길어지는 글. 억지 패딩 금지.
- 대제목(##): 반드시 **굵게(bold)**. 2개·3개·4개 중 하나를 매번 다르게 선택해서 사용한다.
- 소제목(###), 이모지, 리스트(-): 내용에 맞게 적절히.
- 굵게(**bold**): 핵심 키워드·수치·결론 문장에 1~2개/문단.
- 하이라이트(<mark>): 꼭 기억할 핵심 문구 1~2곳.
- 수치는 반드시 일상 비유로 체감시켜라.
  예) "파라미터 1000억 개" → "서울 시민 10명의 뇌 신경세포 수와 맞먹는다"
      "3나노 반도체" → "머리카락 굵기의 3만 분의 1"
- 전문용어 첫 등장 시 괄호로 쉬운 설명 추가.
- 문체: 친근한 평어체. ~다/~이다/~한다. ❌ ~습니다/~요/~죠 금지.
- 각 문단: 할 말 있으면 길게, 없으면 짧게.

[유머 - 글 전체에 1~2곳, 자연스럽게]
- 억지로 넣지 않는다. 맥락이 맞을 때만. 없으면 안 넣어도 된다.
- 허용되는 유머: AI와 인간을 대비한 가벼운 개그("AI한테 물어보니 나보다 잘 알더라"),
  가벼운 말장난·언어유희, 공감되는 자조적 표현("이거 나만 몰랐나?", "알고 나니 더 불안하다"),
  요즘 밈 뉘앙스("이거 실화임?", "소름 돋았으면 손 들어", "~각이다").
- 금지: 특정 집단·인물 비하, 억지 개그, 콘텐츠 흐름을 끊는 유머.
- 유머 위치: 도입부 첫 문장, 대화 구간, 마무리 중 자연스러운 곳 1~2군데면 충분하다.

[외부 링크 - 본문에 반드시 2~3개 삽입]
형식: <a href="https://실제URL" target="_blank">앵커텍스트</a>
신뢰도 순서: 공식 연구기관·기업 발표 > 대형 언론사 > 유명 IT 전문 사이트 > 위키백과
추천 소스 (주제에 맞게 선택):
- NASA 공식 (nasa.gov): AI 활용 탐사 미션, 우주 기술 하위 페이지
- MIT Technology Review (technologyreview.com): 우주×AI 교차 심층 기사
- IEEE Spectrum (spectrum.ieee.org): 우주용 반도체·항공전자 기사
- SpaceNews (spacenews.com): 위성·탐사 기술 뉴스
- Universe Today (universetoday.com): 천문 AI 연구 기사
- 한국천문연구원 (kasi.re.kr): 국내 우주 AI 연구
- 한국어 위키백과 (ko.wikipedia.org): 개념 설명 용어에
- 조선·중앙·한국경제 등 국내 대형 언론사 우주·AI 관련 기사
주의:
  ✅ 홈페이지 루트 금지 — 내용과 직접 관련된 하위 페이지·기사 URL만 사용
  ✅ 앵커텍스트는 자연스러운 한국어 문구로
  ❌ 존재하지 않을 것 같은 URL 지어내지 말 것 — 확실한 URL만 사용"""


# ── 우주산업 글 ───────────────────────────────────────────
def _post_space_industry():
    """우주산업·민간우주·우주경제 트렌드 글"""
    print("  🚀 우주산업 뉴스 수집 중...")
    news = _fetch_industry_news()

    avoid_str = _build_avoid_str(days=60)
    chat_instruction = _build_chat_instruction()

    if news:
        news_text = ""
        for i, n in enumerate(news, 1):
            news_text += f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"
        news_section = f"""---최신 우주산업 뉴스 (참고용 — 직접 번역·복사 금지)---
{news_text}---"""
    else:
        news_section = "# [뉴스 수집 실패] 최근 우주산업 트렌드를 자체적으로 판단해서 작성할 것."

    structures = [
        """\
1. 도입부 (3~4문장): 이 소식이 왜 주목받는지, 우주산업과 돈·비즈니스가 어떻게 연결되는지.
2. ## **[지금 우주에서 무슨 일이 벌어지고 있나]**: 핵심 사실·현황 쉽게 설명.
3. ## **[이게 왜 돈이 되는가 / 비즈니스 관점]**: 시장 규모, 투자 흐름, 기업 경쟁 구도.
4. 마무리 (2~3문장): 우주산업이 우리 삶에 가져올 변화 한 줄 정리.""",

        """\
1. 도입부 (3~4문장): 우주가 더 이상 국가 독점이 아닌 이유부터 시작.
2. ## **[핵심 플레이어와 경쟁 구도]**: SpaceX·Blue Origin·각국 기업·스타트업 현황.
3. ## **[이 분야의 진짜 기회와 리스크]**: 성장 가능성과 현실적 장벽.
4. ## **[한국은 어디쯤 있나]**: 국내 우주산업 현황과 기회.
5. 마무리 (2문장): 짧고 임팩트 있게.""",

        """\
1. 도입부 (3~4문장): 숫자나 반전 사실로 시작 ("우주산업 시장이 XX조를 넘겼다" 등).
2. ## **[무슨 일이 있었나]**: 이번 뉴스·트렌드의 핵심 내용.
3. ## **[기술적 의미]**: 어떤 기술적 도전을 해결했는지, 또는 어떤 기술이 핵심인지.
4. ## **[산업·경제적 파급효과]**: 이 변화가 비즈니스·투자·일상에 미치는 영향.
5. ## **[앞으로의 전망]**: 다음 단계, 경쟁 구도, 남은 과제.
6. 마무리 (2문장): 짧게.""",
    ]
    structure = random.choice(structures)

    prompt = f"""아래 최신 우주산업 뉴스를 참고해서 한국어 블로그 글을 써라.

{news_section}

[작성 원칙]
- 우주과학(과학적 현상)이 아닌 우주산업·우주경제·민간우주·우주 비즈니스 관점으로 써라.
- SpaceX, Blue Origin, Rocket Lab, Axiom Space 같은 기업, 발사 비즈니스, 위성 서비스, 우주여행, 달 경제 등이 주제가 될 수 있다.
- 뉴스를 그대로 번역하지 않는다. "이게 왜 중요한지", "돈과 비즈니스 관점에서 어떤 의미인지"를 풀어준다.
- 전문 용어는 쉽게 풀어 설명. 투자자나 일반인도 이해할 수 있게.

[금지 주제 - 최근 사용됨]
{avoid_str}

[제목 형식]
"SpaceX가 해낸 것", "우주가 돈이 되는 이유", "민간 우주시대가 열렸다" 등 비즈니스·산업 느낌의 제목.

{_common_format_rules()}

{chat_instruction}

[내용 구성]
{structure}

출처 표기 (글 맨 아래, 뉴스 수집 성공 시):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='우주산업')


# ── 잡학 기반 글 ──────────────────────────────────────────
def _post_space_trivia():
    """우주과학 호기심 잡학 글 작성"""
    avoid_str = _build_avoid_str(days=60)

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

        f"""\
1. 도입부 (3~4문장): {intro_style}
2. ## **[많은 사람이 잘못 알고 있는 것]**: 교과서 상식과 다른 진짜 사실.
3. ## **[과학이 밝혀낸 진짜 이유]**: 구체적 수치·근거. 비유로 스케일 체감.
4. ## **[더 파고들면 나오는 것들]**: 관련된 의외의 사실, 최신 연구, 미해결 질문.
5. ## **[지구와 우리 일상으로 이어지는 연결]**: 이 우주 현상이 우리 삶과 어떻게 맞닿아 있나.
6. 마무리 (2문장): 짧고 여운 있게.""",
    ]
    structure = random.choice(structures)
    chat_instruction = _build_chat_instruction()

    prompt = f"""아래 조건에 맞는 우주과학 블로그 글을 써라.

[주제 선택]
우주·천문학·행성·별·은하·블랙홀·탐사선·우주론·물리법칙 등 우주과학 전반에서 하나를 골라라.
"블랙홀에 빨려 들어가면 어떻게 될까?", "달은 왜 지구 주위를 돌까?",
"태양이 사라지면 지구는 8분 후에야 알 수 있다", "우주는 계속 팽창 중이다" 처럼
규모가 크고 상상력을 자극하거나, 알고 나면 세계관이 흔들리는 주제로.
전공자가 아닌 일반인도 술술 읽힐 수 있도록 쉽게 써라.

[금지 주제 - 최근 사용됨, 의미상 비슷한 것도 피할 것]
{avoid_str}

[제목 형식]
"~하면 어떻게 될까?", "사실 ~였다", "~의 진짜 크기", "우주에서 ~가 가능할까?" 등 호기심·스케일 자극 형식.

{_common_format_rules()}

{chat_instruction}

[내용 구성]
{structure}

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='잡학')


# ── AI/반도체 뉴스 글 (목) ───────────────────────────────
def _post_ai_news():
    """최신 AI·반도체 뉴스를 바탕으로 한국어 블로그 글 작성"""
    print("  🤖 AI/반도체 최신 뉴스 수집 중...")
    news = _fetch_ai_news(AI_NEWS_FEEDS)

    avoid_str = _build_avoid_str(days=60)
    chat_instruction = _build_chat_instruction()

    if not news:
        print("  ⚠ 뉴스 수집 실패 → AI 트렌드 글로 대체")
        return _post_ai_trend()

    news_text = ""
    for i, n in enumerate(news, 1):
        news_text += f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"

    structures = [
        """\
패턴1 (H2 2개):
1. 도입부 (3~4문장): 이 뉴스가 왜 주목받는지.
2. ## **[무슨 일이 있었나]**: 핵심 사실 쉽게 설명. 수치·비유 필수.
3. ## **[이게 왜 중요한가]**: 기술적·산업적 의미, 우리 일상에 미치는 영향.
4. 마무리 (2~3문장): 앞으로 어떻게 될지 한 줄 전망.""",

        """\
패턴2 (H2 3개):
1. 도입부 (3~4문장): 이 뉴스가 왜 주목받는지.
2. ## **[무슨 일이 있었나]**: 핵심 사실 쉽게 설명.
3. ## **[기술적으로 어떤 의미인가]**: 원리·배경 설명. 전문용어는 쉽게 풀어서.
4. ## **[산업·일상에 미치는 영향]**: 기업·소비자·시장 관점.
5. 마무리 (2문장): 짧고 임팩트 있게.""",

        """\
패턴3 (H2 4개):
1. 도입부 (3~4문장): 반전 사실이나 숫자로 시작.
2. ## **[배경 — 여기까지 어떻게 왔나]**: 이 기술·사건의 맥락.
3. ## **[무슨 일이 있었나]**: 핵심 사실. 수치·비유 필수.
4. ## **[기술적 의미]**: 어떤 혁신인지, 기존과 뭐가 다른지.
5. ## **[앞으로 어떻게 될까]**: 후속 전망, 경쟁 구도, 남은 과제.
6. 마무리 (2문장): 짧고 강렬하게.""",
    ]
    structure = random.choice(structures)

    prompt = f"""아래 최신 AI·반도체 뉴스들을 참고해서 한국어 블로그 글을 써라.

---최신 AI·반도체 뉴스 (참고용 — 직접 번역·복사 금지)---
{news_text}---

[작성 원칙]
- 뉴스 중 가장 흥미롭고 임팩트 있는 것 1개를 골라 중심 주제로 삼아라.
- 반드시 **우주 탐사·천문학·위성·로켓과 AI·반도체가 만나는 지점**을 다뤄라.
  예) AI가 외계행성을 어떻게 찾는지, 탐사 로버에 탑재된 AI 칩, 망원경 데이터를 분석하는 머신러닝,
      우주 환경에서 살아남는 방사선 내성 반도체, NASA의 AI 자율 탐사 시스템 등.
- 뉴스를 그대로 번역하거나 요약하지 않는다. "이 기술이 우주 탐사를 어떻게 바꾸는지"를 설명하는 글을 쓴다.
- 전문용어는 반드시 쉬운 말로 풀어서 설명한다.
- 읽고 나서 "AI가 우주에서 이런 것도 하는구나!" 반응이 나오게.

[금지 주제 - 최근 사용됨]
{avoid_str}

[제목 형식]
"AI가 발견한 ~", "우주 탐사에 AI가 쓰이는 법", "반도체가 우주를 바꾼다" 등 우주×AI 교차점이 드러나는 제목.
단, 낚시성 제목 금지 — 본문 내용과 일치해야 한다.

{_ai_format_rules()}

{chat_instruction}

[내용 구성 — 아래 중 하나를 선택]
{structure}

출처 표기 (글 맨 아래):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='AI뉴스')


# ── AI/반도체 트렌드 글 (금) ─────────────────────────────
def _post_ai_trend():
    """AI·반도체 산업 트렌드·기술 이슈 글"""
    print("  💡 AI/반도체 트렌드 뉴스 수집 중...")
    news = _fetch_ai_news(AI_TREND_FEEDS)

    avoid_str = _build_avoid_str(days=60)
    chat_instruction = _build_chat_instruction()

    if news:
        news_text = ""
        for i, n in enumerate(news, 1):
            news_text += f"\n[뉴스 {i}]\n제목: {n['title']}\n출처: {n['source']}\nURL: {n['url']}\n내용: {n['summary']}\n"
        news_section = f"""---최신 AI·반도체 트렌드 뉴스 (참고용 — 직접 번역·복사 금지)---
{news_text}---"""
    else:
        news_section = "# [뉴스 수집 실패] 최근 AI·반도체 산업 트렌드를 자체적으로 판단해서 작성할 것."

    structures = [
        """\
1. 도입부 (3~4문장): 이 기술·트렌드가 왜 지금 주목받는지.
2. ## **[지금 무슨 일이 벌어지고 있나]**: 핵심 현황 쉽게 설명.
3. ## **[왜 중요한가 / 비즈니스 관점]**: 시장 규모, 기업 경쟁 구도, 투자 흐름.
4. 마무리 (2~3문장): 이 트렌드가 우리 일상이나 산업에 가져올 변화.""",

        """\
1. 도입부 (3~4문장): 숫자나 반전 사실로 시작 ("AI 시장이 XX조를 넘겼다" 등).
2. ## **[핵심 플레이어와 경쟁 구도]**: 빅테크·스타트업·국내 기업 현황.
3. ## **[이 분야의 진짜 기회와 리스크]**: 성장 가능성과 현실적 장벽.
4. ## **[한국은 어디쯤 있나]**: 국내 AI/반도체 현황과 기회.
5. 마무리 (2문장): 짧고 임팩트 있게.""",

        """\
1. 도입부 (3~4문장): AI·반도체 트렌드와 일상의 연결로 시작.
2. ## **[기술의 현재 위치]**: 지금 어디까지 왔는지, 뭐가 가능해졌는지.
3. ## **[기술적 핵심 — 어떻게 작동하는가]**: 핵심 원리를 일반인도 이해하게 쉽게.
4. ## **[산업·경제적 파급효과]**: 이 기술이 비즈니스·일자리·소비자에 미치는 영향.
5. ## **[앞으로의 전망]**: 다음 단계, 해결해야 할 과제.
6. 마무리 (2문장): 짧게.""",
    ]
    structure = random.choice(structures)

    prompt = f"""아래 최신 AI·반도체 트렌드 뉴스를 참고해서 한국어 블로그 글을 써라.

{news_section}

[작성 원칙]
- 반드시 **우주 기술과 AI·반도체의 교차점**을 다뤄라.
  예) 우주용 AI 칩 개발 경쟁, 위성 데이터를 분석하는 머신러닝, 자율 항법 AI, 우주 방사선에 강한 반도체,
      제임스 웹 망원경 데이터 처리 AI, SpaceX 로켓 자동 착륙 알고리즘, 달·화성 기지를 위한 AI 등.
- 뉴스를 그대로 번역하지 않는다. "이 기술이 우주 탐사에서 어떤 의미인지"를 풀어준다.
- 전문 용어는 쉽게 풀어 설명. 비전공자도 이해할 수 있게.

[금지 주제 - 최근 사용됨]
{avoid_str}

[제목 형식]
"우주에서 AI가 하는 일", "위성을 움직이는 반도체", "우주 탐사를 바꾸는 기술" 등 우주×AI 교차점 느낌의 제목.

{_ai_format_rules()}

{chat_instruction}

[내용 구성]
{structure}

출처 표기 (글 맨 아래, 뉴스 수집 성공 시):
<p style="font-size:0.85em;color:#999;margin-top:2em;">📰 참고: <a href="뉴스URL" target="_blank">출처명</a></p>

{_meta_output_rules()}"""

    return _run_and_publish(prompt, mode='AI트렌드')


# ── 공통 실행·발행 ─────────────────────────────────────────
def _run_and_publish(prompt: str, mode: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    print(f"  Claude API 호출 중 (우주과학 / {mode})...")
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

    image_query = result.get('image_query', 'space galaxy universe stars')
    print(f"  이미지 검색: {image_query}")
    featured_image = fetch_featured_image(image_query, nasa=True)
    body_images    = fetch_multiple_images(image_query, count=3, nasa=True)

    if featured_image:
        print(f"  대표 이미지: {featured_image['credit']}")
    if body_images:
        print(f"  본문 이미지: {len(body_images)}장")

    post_result = publish_post(
        title=result['title'],
        content_html=result['content_html'],
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
        topic=f'우주과학({mode})',
        site='newbicon_space',
    )

    print(f"  ✅ 우주과학({mode}) 임시글 저장 완료! ID: {post_result['id']} / {post_result['url']}")
    return post_result


# ── 진입점 ────────────────────────────────────────────────
DAY_NAMES = {0: '월요일', 1: '화요일', 2: '수요일', 3: '목요일', 4: '금요일'}

def post_space():
    weekday = datetime.now(KST).weekday()  # 0=월 ... 4=금
    day = DAY_NAMES.get(weekday, '')

    if weekday in NEWS_DAYS:
        print(f"  📰 오늘은 {day} → 우주 최신 뉴스 글")
        return _post_space_news()
    elif weekday in TRIVIA_DAYS:
        print(f"  🔭 오늘은 {day} → 우주 잡학 글")
        return _post_space_trivia()
    elif weekday in INDUSTRY_DAYS:
        print(f"  🏭 오늘은 {day} → 우주산업 글")
        return _post_space_industry()
    elif weekday in AI_NEWS_DAYS:
        print(f"  🤖 오늘은 {day} → AI/반도체 뉴스 글")
        return _post_ai_news()
    else:  # AI_TREND_DAYS
        print(f"  💡 오늘은 {day} → AI/반도체 트렌드 글")
        return _post_ai_trend()


if __name__ == '__main__':
    post_space()
