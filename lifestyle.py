"""
lifestyle.py - 블랙넛지 라이프스타일 포스팅 (주 4회)
공식: [흥미로운 스토리] + [오늘 당장 써먹는 실용 정보]
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import random
from datetime import datetime
from llm import call_llm
from dotenv import load_dotenv
load_dotenv()

from writer import parse_output, build_internal_links_prompt, build_seo_prompt
from wordpress import publish_post, fetch_recent_posts
from images import fetch_featured_image, fetch_multiple_images
from topic_tracker import get_recent_keywords, get_recent_titles, save_topic
from trending import search_recent_articles, build_freshness_section

# ★ blacknudge '라이프스타일' 카테고리 ID — WordPress 관리자 → 카테고리에서 확인 후 입력
CATEGORY_ID = None

BLOG_NAME = '블랙넛지'

WP_ENV = {
    'wp_url_env':  'WP_URL',
    'wp_user_env': 'WP_USER',
    'wp_pass_env': 'WP_APP_PASSWORD',
}

# ── 테마 풀 ────────────────────────────────────────────────
THEMES = [
    {
        'name': '음식/문화',
        'ideas': [
            '[조선 왕들의 해장법으로 보는 현대식 편의점 해장 꿀조합]',
            '[알고 마시면 2배 맛있는 생맥주·캔맥주 페어링 가이드]',
            '[왜 배달 음식은 포장 음식보다 더 맛없어질까 — 배달 용기·거리별 주문 최적 가이드]',
            '[일본 편의점이 한국 편의점보다 맛있는 진짜 이유 — 따라 할 수 있는 편의점 먹방 팁]',
            '[커피 한 잔에 왜 가격 차이가 10배 날까 — 가격대별 원두 선택 가이드]',
            '[한국인이 유독 매운 음식을 좋아하는 이유 — 내 매운맛 내성 레벨 테스트]',
        ],
        'practical_keyword': '오늘 먹을 것·살 것에 바로 적용하는 가이드, 편의점·마트 추천, 주문 팁',
    },
    {
        'name': '여행/외출',
        'ideas': [
            '[디지털 노마드 한달살기 현실 영수증 — 치앙마이·발리·리스본 비교]',
            '[혼자 뛰는 러너를 위한 서울 야간 러닝 코스 비밀 지도]',
            '[KTX vs 비행기 vs 고속버스 — 목적지별 현실 시간·비용 비교 시트]',
            '[국내 카페 캠핑장 베스트 — 텐트 없이도 감성 캠핑 되는 곳]',
            '[처음 혼자 해외여행 가는 사람을 위한 48시간 일정 짜기 공식]',
            '[서울 근교 당일치기 꽃놀이 코스 — 주차 되고 붐비지 않는 곳]',
        ],
        'practical_keyword': '실제 비용 영수증, 구체적 코스·일정, 예약 방법, 체크리스트',
    },
    {
        'name': '건강/운동',
        'ideas': [
            '[하루 10분 운동이 1시간보다 효과적인 이유 — 직장인 데스크 루틴 5가지]',
            '[물 하루 2L 마시는 게 정말 맞나 — 내 체중에 맞는 수분 계산법]',
            '[수면 6시간과 8시간의 진짜 차이 — 최적 수면 시간 찾는 2주 실험법]',
            '[러닝 vs 걷기 — 체지방 감량에 진짜 더 효과적인 건 무엇인가]',
            '[탄수화물을 끊으면 안 되는 이유 — 직장인 점심 탄수화물 최적 조합]',
            '[스트레칭을 운동 전에 하면 안 되는 과학적 이유 — 올바른 워밍업 순서]',
        ],
        'practical_keyword': '오늘부터 바로 실천하는 루틴, 주간 플랜, 운동법 단계별 가이드',
    },
    {
        'name': '생활 꿀팁',
        'ideas': [
            '[집 정리가 안 되는 진짜 이유 — 3일 안에 방 바꾸는 물건 배치 공식]',
            '[스마트폰 배터리 수명이 빨리 줄어드는 5가지 습관과 교정 방법]',
            '[통신비 월 3만원 줄이는 법 — 알뜰폰·요금제·앱 조합 실전 가이드]',
            '[쿠팡·네이버쇼핑 최저가 찾는 꿀팁 — 가격 추적 앱 완전 정복]',
            '[집에서 카페 라떼 맛 내는 법 — 우유 거품 내는 도구별 비교 (1만원대부터)]',
            '[집 냄새 없애는 방법 — 향초·디퓨저 없이 공기질 올리는 루틴]',
        ],
        'practical_keyword': '즉시 실행 가능한 방법, 앱·제품 추천 (가격 포함), 단계별 가이드',
    },
    {
        'name': '재테크/소비',
        'ideas': [
            '[구독 서비스 다이어트 — 지금 당장 끊어야 할 것과 유지해야 할 것 분류법]',
            '[편의점 할인·적립 최대화 꿀팁 — 월 5만원 절약하는 편의점 루틴]',
            '[첫 달 월급 30만원 저축으로 시작하는 적금 vs 주식 vs CMA 비교]',
            '[배달앱 수수료의 진실 — 배달 시킬 때 손해 안 보는 시간·메뉴 선택법]',
            '[연봉 협상이 두려운 사람을 위한 현실적인 근거 만들기 가이드]',
            '[체크카드 vs 신용카드 — 소비 패턴별 연간 손익 계산해보기]',
        ],
        'practical_keyword': '오늘 당장 실행하는 절약법, 비교 분석표, 실전 금액 계산',
    },
    {
        'name': '뷰티/패션',
        'ideas': [
            '[세안제보다 세안법이 더 중요한 이유 — 피부 트러블 줄이는 올바른 세안 순서]',
            '[자외선 차단제 SPF 숫자의 진실 — 내 피부에 맞는 선크림 고르는 법]',
            '[옷 많은데 입을 게 없는 이유 — 미니멀 옷장 만드는 3·3·3 법칙]',
            '[여름 장마철 두피 냄새 없애는 법 — 샴푸 방법보다 건조 방법이 핵심이다]',
            '[남성 피부 관리 5분 루틴 — 스킨·로션 없이 시작하는 초보 그루밍]',
            '[운동화 오래 신는 법 — 세탁·보관·교체 시기 완전 정리]',
        ],
        'practical_keyword': '오늘부터 바꾸는 루틴, 가성비 제품 추천, 단계별 방법',
    },
]


def _pick_theme_and_avoid() -> tuple[dict, str]:
    """랜덤 테마 선택 + 중복 방지 문자열"""
    theme = random.choice(THEMES)
    keywords = get_recent_keywords(days=60, site='blacknudge_lifestyle')
    titles   = get_recent_titles(days=60, site='blacknudge_lifestyle')
    lines = []
    if keywords:
        lines.append('최근 키워드: ' + ', '.join(keywords[-30:]))
    if titles:
        lines.append('최근 제목 (이 주제들과 겹치거나 의미상 비슷한 것 금지):')
        for t in titles[-20:]:
            lines.append(f'  - {t}')
    avoid_str = '\n'.join(lines) if lines else '없음'
    return theme, avoid_str


def _build_chat_instruction() -> str:
    if random.random() < 0.5:
        return f"""\
[대화 구간 — 어려운 내용이나 복잡한 개념을 쉽게 풀 때 사용]
- 글 중간에서 딱 1번만 사용. 3~5번 주고받는다.
- 말투: 친한 친구 사이, 짧고 자연스럽게.
  {BLOG_NAME}은 ~야/~거야/~잖아/~지/~어 구어체.
  독자는 "진짜?", "그게 왜?", "얼마나?", "그래서?" 짧게 반응.
  ❌ 금지: ~입니다, ~습니다, ~이다, ~한다
- 대화 중 핵심 단어·중요한 수치·핵심 문장에는 **굵게** 표시. 예: **하루 10분**, **세 배 차이남**
[CHAT]
{BLOG_NAME}: (설명)
독자: (짧은 반응)
{BLOG_NAME}: (이어서)
독자: (반응)
{BLOG_NAME}: (마무리)
[/CHAT]"""
    return "# [대화 구간 없음] 대화 블록 없이 본문으로만 구성한다."


def _build_prompt(theme: dict, avoid_str: str, chat: str, internal_links: str = "", freshness_section: str = "") -> str:
    example_ideas = '\n'.join(f'  - {idea}' for idea in theme['ideas'][:4])

    structures = [
        """\
① 도입부 (3~4문장): 역사적 사실·과학 원리·트렌드를 흥미롭게 시작.
   독자가 "어, 이건 나도 궁금했는데" 혹은 "오 이런 게 있었어?" 반응이 나와야 한다.
② ## **[스토리 — 왜 이게 흥미로운가]**: 배경 지식·역사·원리를 구체적으로 풀기.
   수치·이름·연도·에피소드 포함. 비유로 쉽게.
③ ## **[그래서 지금 나는 어떻게 해야 하나]**: 오늘 당장 적용하는 실용 정보.
   특정 제품명·장소·가격·순서를 명시. "추천드립니다" 같은 모호한 표현 금지.
④ 마무리 (2~3문장): "이걸 알고 나서 달라진 것"으로 마무리.""",

        """\
① 도입부 (3~4문장): 의외의 사실이나 반전으로 시작.
   "사실 많은 사람이 반대로 알고 있다", "이게 상식인 줄 알았는데..." 식.
② ## **[흔한 오해 / 대부분이 모르는 것]**: 기존 상식과 다른 사실.
③ ## **[진짜 이유 / 올바른 방법]**: 과학적·실제 근거로 정확하게. 비유 필수.
④ ## **[오늘 바로 써먹는 방법]**: 구체적 실천 방법. 단계별 또는 목록 형식.
   제품명·앱 이름·예상 비용·소요 시간 포함.
⑤ 마무리 (2문장): 짧고 임팩트 있게.""",

        """\
① 도입부 (3~4문장): 독자에게 직접 질문 던지기.
   "혹시 이런 경험 있어?", "이 숫자 들으면 어떻게 반응해?" 식으로 끌어들이기.
② ## **[스토리 — 배경이 있어야 실용이 빛난다]**: 역사·문화·과학 배경.
   단순 나열이 아니라 '왜 이게 지금도 유효한가'까지 연결.
③ ## **[실전 가이드 — 이렇게 하면 된다]**: 구체적인 행동 방법.
   ✅ 포함 필수: 특정 상품명 또는 장소, 예상 비용, 소요 시간, 주의사항.
④ ## **[더 잘 써먹는 꿀팁]**: 위 가이드를 레벨업하는 추가 팁 2~3가지.
⑤ 마무리 (2~3문장): 한 줄 정리 + "나도 해봐야겠다" 자극.""",

        """\
① 도입부 (3~4문장): 트렌드나 요즘 뜨는 것으로 시작.
   "요즘 ~하는 사람들이 부쩍 늘었는데", "SNS에서 난리 난 이유가 있었다" 식.
② ## **[왜 지금 이게 뜨고 있나]**: 트렌드의 배경과 원리. 데이터·수치 포함.
③ ## **[실제로 해보려면 — 현실 가이드]**: 구체적 방법·비용·준비물.
   비용 영수증 스타일 (숙소 X원 + 식비 X원 = 합계 X원) 또는 체크리스트 형식 권장.
④ 마무리 (2~3문장): 처음 시작하는 사람을 위한 한 줄 조언.""",
    ]

    structure = random.choice(structures)

    return f"""블랙넛지 블로그에 올릴 라이프스타일 글을 써라.

[블로그 방향]
블랙넛지는 "재미있는 이야기 + 오늘 당장 써먹는 정보"를 파는 블로그다.
단순 정보 나열이나 백과사전식 설명 글 금지.
독자가 읽고 나서 "어, 나도 해봐야겠다" 또는 "이거 지금 당장 써먹어야지"라는 반응이 나와야 한다.

[오늘의 테마: {theme['name']}]
{theme['practical_keyword']}

[아이디어 예시 — 이 중 하나를 고르거나, 더 좋은 아이디어로 대체 가능]
{example_ideas}

[글의 핵심 공식]
① 스토리 파트: 역사적 사실 / 과학적 원리 / 문화·트렌드 배경
   → 독자가 "오, 이게 왜 그랬어?" 하고 빠져드는 이야기. 구체적 수치·에피소드 포함.
② 실용 파트: 그래서 지금 내가 뭘 어떻게 해야 하는가
   → 제품명, 장소명, 실제 비용, 순서, 체크리스트 등 지금 바로 행동할 수 있는 정보.
   → "~하면 좋습니다" 식의 모호한 표현 절대 금지. 구체적이고 솔직하게.

[최신 정보 원칙 — 제품·서비스·가격 언급 시 필수]
오늘 날짜: {datetime.now().strftime('%Y년 %m월 %d일')}
- 특정 제품 모델명 추천 시: 출시 2년 이내 제품만 언급. 단종·단산 가능성이 있는 구형 모델 금지.
- 모델명이 불확실하면: 모델명 대신 스펙/가격대/브랜드 계열로 설명.
  ❌ "다이슨 HD08 추천" → ✅ "다이슨 슈퍼소닉 최신 라인업 (20만원대)"
  ❌ "샤오미 3세대" → ✅ "3만원대 가성비 드라이기"
- 가격 수치: 구체적 가격 대신 "~만원대" 표현 사용.
- 글 실용 파트 마지막에 한 줄 추가: "※ 가격·재고는 변동될 수 있으니 구매 전 최신 정보를 확인하세요."
{freshness_section}

[금지 주제 — 최근 발행됨, 의미상 비슷한 것도 피할 것]
{avoid_str}

[제목 형식]
"[실천 유형] + 스토리 연결" 또는 "이야기 + 실전 가이드" 형식.
예) "조선 왕 해장법으로 배우는 편의점 숙취 해소 꿀조합 3선"
    "배달음식이 포장보다 맛없어지는 과학적 이유와 주문 최적화 방법"
    "한달살기 치앙마이 현실 비용 영수증 — 최소 생존 비용 계산해봤다"

{build_seo_prompt()}

[모바일 최적화 — 가독성 필수 조건]
- 문단 길이: 2~3문장이면 반드시 줄 바꿈. 스마트폰 화면에서 한 문단이 5줄을 넘으면 안 된다.
- 문장 길이: 한 문장에 50자 이내. 길어지면 둘로 쪼갠다.
- 3개 이상 나열: 반드시 리스트(- ) 형식. 문장 안에 쉼표로 나열 금지.
- 수치·단계·비교: 표(Markdown `| 헤더 | 헤더 |` 형식) 또는 리스트(- ) 형식으로 시각화. 표는 자동으로 HTML 테이블로 변환된다.
- 굵게(**bold**)로 핵심 정보를 부각 — 스캐닝하는 독자가 굵은 글씨만 읽어도 핵심을 알 수 있어야 함.
- 텍스트 덩어리(벽돌 텍스트) 절대 금지. 줄 바꿈·리스트·대제목으로 여백을 만든다.

[형식 조건]
- 분량: 600~800단어 (한국어 약 2400~3200자). 800단어를 절대 넘지 않는다.
- 대제목(##): 반드시 **굵게(bold)**. 2~4개 중 매번 다르게.
- 소제목(###): 각 ## 대제목 아래에 1~2개 반드시 사용. 내용을 잘게 나눠 읽기 쉽게.
- 이모지: 소제목·대제목 앞에 맥락에 맞게 적절히.
- 리스트(-): 3개 이상 나열 시 필수.
- 굵게(**bold**): 핵심 수치·제품명·행동 지침에 1~2개/문단.
- 하이라이트(<mark>): 독자가 꼭 기억할 핵심 정보 1~2곳.
- 비용·시간 등 수치는 반드시 포함. 비교할 수 있게 제시.
- 전문용어 첫 등장 시 괄호로 쉬운 설명.
- 문체: 친구한테 설명하듯 쉽고 편하게. ~다/~이다/~한다.
  ❌ 딱딱한 기사체 금지: "~것으로 전해졌다", "~에 따르면" 같은 표현 절대 금지.
  ✅ "솔직히", "이게 진짜 포인트인데", "쉽게 말하면", "한마디로" 같은 표현 적극 활용.
  ❌ ~습니다/~요/~죠 금지.

[유머 — 1~2곳, 자연스럽게]
공감되는 자조적 표현("이거 나만 몰랐나?"), 가벼운 과장("이래서 내 지갑이 얇았구나"),
요즘 밈 뉘앙스("이거 진짜 실화임?"). 억지 개그 금지.

[외부 링크 — 본문에 반드시 2~3개]
형식: <a href="https://실제URL" target="_blank">앵커텍스트</a>
신뢰도 순서: 공공기관·대형 언론사 > 전문 사이트 > 위키백과·나무위키
✅ 내용과 직접 관련된 하위 페이지·기사 URL만 (홈페이지 루트 금지)
✅ 앵커텍스트는 자연스러운 한국어 문구로
❌ 확실하지 않은 URL 지어내지 말 것

{chat}

[내용 구성]
{structure}

{internal_links}

[자체 검수 — 출력 전 필수 확인]
글을 다 쓴 뒤 아래 4가지를 점검한다. 문제가 있으면 해당 부분을 수정한 최종본만 출력한다.
① 모든 문단이 제목·메인 주제와 직접 연결되는가? 관련 없는 문단은 삭제한다.
② "흥미롭지만 이 글의 주제와 무관한" 정보가 끼어 있지 않은가?
③ 실용 파트의 팁·제품 추천이 이번 글의 핵심 주제 안에 있는가?
④ 각 대제목(##) 하위 내용이 그 대제목 범위에서 벗어나지 않는가?

---
글 본문이 끝나면 반드시 아래 5줄 출력. 절대 빠뜨리지 말 것.
FOCUS_KEYWORD: 핵심 검색어(2~4단어)
SEO_TITLE: SEO 제목(60자 이내, 포커스 키워드 앞쪽)
SEO_DESCRIPTION: 메타 설명(150~160자, 포커스 키워드 포함, 클릭 유도)
IMAGE_QUERY: 글 핵심 장면 영어 3~5단어 (구체적 사물·장면, 추상어 금지)
  예) 편의점 해장 → "korean convenience store food hangover"
      야간 러닝  → "night running park city lights jogger"
TAGS: 태그1,태그2,태그3,태그4,태그5"""


def post_lifestyle():
    theme, avoid_str = _pick_theme_and_avoid()
    chat = _build_chat_instruction()
    print(f"  오늘의 라이프스타일 테마: [{theme['name']}]")

    print("  🔗 내부 링크용 최근 발행글 조회 중...")
    recent_posts = fetch_recent_posts(WP_ENV, count=8)
    internal_links = build_internal_links_prompt(recent_posts)
    if recent_posts:
        print(f"    발행글 {len(recent_posts)}건 확인")

    # 최신 기사 검색 (90일 이내) — 단종 제품·구식 정보 방지
    search_query = f"{theme['practical_keyword']} 추천 최신"
    print(f"  🔍 최신 정보 수집 중: '{search_query}'")
    articles = search_recent_articles(search_query, count=6, days=90)
    freshness_section = build_freshness_section(search_query, articles)
    if articles:
        print(f"    최신 기사 {len(articles)}건 확인")
    else:
        print("    최신 기사 없음 (프롬프트 날짜 규칙으로 대체)")

    prompt = _build_prompt(theme, avoid_str, chat, internal_links, freshness_section)

    print("  Gemini API 호출 중 (라이프스타일)...")
    raw = call_llm(prompt, max_tokens=8096, use_search=True)
    result = parse_output(raw, blog_name=BLOG_NAME)

    print(f"  제목: {result['title']}")
    print(f"  본문: {len(result['content_markdown'])}자")
    print(f"  포커스 키워드: {result.get('focus_keyword', '-')}")

    image_query = result.get('image_query', 'lifestyle korea daily life')
    print(f"  이미지 검색: {image_query}")
    featured_image = fetch_featured_image(image_query)
    body_images    = fetch_multiple_images(image_query, count=3)

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
        topic=f'라이프스타일({theme["name"]})',
        site='blacknudge_lifestyle',
    )

    print(f"  ✅ [{theme['name']}] 임시글 저장 완료! ID: {post_result['id']} / {post_result['url']}")
    return post_result


if __name__ == '__main__':
    post_lifestyle()
