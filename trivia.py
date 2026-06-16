"""
trivia.py - '잡학' 카테고리 블랙넛지 포스팅
생활 잡학(일상 속 왜?)과 지식 잡학(과학·역사·자연)을 하루씩 번갈아 발행
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import random
import anthropic
from dotenv import load_dotenv
load_dotenv()

from writer import parse_output
from wordpress import publish_post
from images import fetch_featured_image, fetch_multiple_images
from topic_tracker import get_recent_keywords, get_recent_titles, save_topic, load_used_topics

# ★ blacknudge '잡학' 카테고리 ID — WordPress 관리자 → 카테고리에서 확인 후 입력
CATEGORY_ID = None

BLOG_NAME = '블랙넛지'

WP_ENV = {
    'wp_url_env':  'WP_URL',
    'wp_user_env': 'WP_USER',
    'wp_pass_env': 'WP_APP_PASSWORD',
}


def _get_next_type() -> str:
    """used_topics.json의 마지막 잡학 글 유형을 읽어 반대 유형 반환.
    trivia_state.json 대신 이미 GitHub에 커밋되는 used_topics.json 기반으로 동작."""
    topics = load_used_topics()
    for t in reversed(topics):
        if t.get('site') == 'health_trivia':
            topic_str = t.get('topic', '')
            if '생활' in topic_str:
                print("  마지막: 생활 잡학 → 이번: 지식 잡학")
                return '지식'
            elif '지식' in topic_str:
                print("  마지막: 지식 잡학 → 이번: 생활 잡학")
                return '생활'
    # 기록 없으면 생활부터 시작
    print("  최근 기록 없음 → 생활 잡학으로 시작")
    return '생활'


# ── 주제 선택 프롬프트 ──────────────────────────────────────
TOPIC_PROMPT = {
    '생활': """\
[주제 유형: 생활 잡학]
일상생활 속에서 누구나 겪지만 왜 그런지 제대로 모르는 것들을 골라라.
아래 분야에서 하나를 직접 선택한다:
- 신체·감각: "왜 하품은 전염될까?", "왜 손이 자고 나면 부어 있을까?", "왜 매운 걸 먹으면 땀이 날까?"
- 음식·주방: "왜 라면은 꼭 끓여야 맛있을까?", "왜 고기는 굽기 전에 상온에 꺼내야 할까?"
- 날씨·자연: "왜 비 오기 전에 냄새가 날까?", "왜 여름에 번개가 많을까?"
- 동물·식물: "왜 고양이는 좁은 데 들어가려 할까?", "왜 개는 코가 젖어 있을까?"
- 생활 속 현상: "왜 새 차는 특유의 냄새가 날까?", "왜 오래된 책에서 특유의 냄새가 날까?"
- 심리·행동: "왜 이름이 생각 안 날 때 천장을 보게 될까?", "왜 거울 속 나는 사진 속 나와 다를까?"
누구나 경험했지만 이유를 모르는 생활밀착형 주제 하나를 골라라.
너무 학문적이거나 어렵지 않게. 읽고 나서 "아 그래서 그랬구나!" 반응이 나오게.""",

    '지식': """\
[주제 유형: 지식 잡학]
과학·자연·역사·동물·인체·우주·음식·언어 등 어떤 분야든 좋다.
"왜 하늘은 파란색일까?", "얼음은 왜 물보다 가벼울까?", "빛은 왜 직진할까?",
"공룡은 왜 그렇게 커졌을까?", "인간은 왜 다른 동물보다 오래 살까?" 처럼
알고 나면 세상이 다르게 보이는 호기심 주제 하나를 골라라.
일상과 살짝 거리가 있어도 괜찮다 — 단, 읽기 쉽고 흥미로워야 한다.
읽고 나서 "오! 몰랐다" 또는 "생각해보니 신기하다" 반응이 나오게.""",
}


def post_trivia():
    trivia_type = _get_next_type()
    print(f"  오늘의 잡학 유형: [{trivia_type} 잡학]")

    keywords = get_recent_keywords(days=60, site='health_trivia')
    titles   = get_recent_titles(days=60, site='health_trivia')
    avoid_lines = []
    if keywords:
        avoid_lines.append('최근 키워드: ' + ', '.join(keywords[-30:]))
    if titles:
        avoid_lines.append('최근 제목 (이 주제들과 겹치거나 의미상 비슷한 것 금지):')
        for t in titles[-20:]:
            avoid_lines.append(f'  - {t}')
    avoid_str = '\n'.join(avoid_lines) if avoid_lines else '없음'

    # 도입부 스타일 랜덤
    intro_styles = [
        '1인칭 경험담으로 시작 ("나는", "어릴 때", "문득 궁금했는데" 등)',
        '독자에게 직접 질문 던지기 ("혹시 생각해본 적 있어?", "이거 제대로 아는 사람 얼마나 될까" 등)',
        '의외의 사실·반전으로 시작 ("사실 이거 아는 사람 드물어", "~인 줄 알았는데 완전 반대였다" 등)',
        '주변 에피소드로 시작 ("친구가 갑자기 물어봤는데", "아이가 물어서 대답하려다가" 등)',
    ]
    intro_style = random.choice(intro_styles)

    # 구성 패턴 랜덤
    structures = [
        f"""\
1. 도입부 (3~4문장): {intro_style}
2. ## **[왜 그런지 핵심 원인]**: 진짜 이유를 쉽게 풀기. 비유·예시 필수. 충분히 길게.
3. ## **[더 깊이 파고들면]**: 관련 흥미 사실, 의외의 연결고리.
4. 마무리 (2~3문장): 짧고 임팩트 있게.""",

        f"""\
1. 도입부 (3~4문장): {intro_style}
2. ## **[흔한 오해]**: 대부분 이렇게 알고 있는데...
3. ## **[진짜 이유]**: 실제로는 이렇다. 구체적 설명.
4. ## **[알고 나면 보이는 것들]**: 이 원리가 일상 어디에 있는지.
5. 마무리 (2문장): 짧게.""",

        f"""\
1. 도입부 (3~4문장): {intro_style}
2. ## **[질문 파헤치기]**: 단계적으로 쉽게 설명. 비유 활용.
3. ## **[실생활에서 발견하는 법]**: 이 원리가 어디에 쓰이는지, 어디서 볼 수 있는지.
4. 마무리 (2~3문장): 한 줄 정리 + 여운.""",

        f"""\
1. 도입부 (3~4문장): {intro_style}
2. ## **[많은 사람이 잘못 알고 있는 것]**: 흔한 오해 또는 반만 맞는 상식.
3. ## **[진짜 이유]**: 과학적·실제 근거로 정확하게 설명. 비유 필수.
4. ## **[더 흥미로운 사실]**: 관련된 의외의 정보, 연결고리, 확장 지식.
5. ## **[일상에서 직접 확인하는 법]**: 이 원리를 오늘 바로 체감할 수 있는 방법.
6. 마무리 (2문장): 짧고 임팩트 있게.""",
    ]
    structure = random.choice(structures)

    # 대화 구간 랜덤 포함 여부 (50%)
    use_chat = random.random() < 0.5
    if use_chat:
        chat_instruction = f"""\
[대화 구간 - 어려운 내용 쉽게 풀기]
- 글 중간 내용이 어려워지는 지점에서 아래 형식의 대화 블록을 정확히 1개 삽입한다.
- 대화는 3~5번 주고받는다.
- 말투: 친한 친구끼리 편하게 얘기하는 느낌. 짧고 자연스럽게.
  {BLOG_NAME}은 ~야/~거야/~잖아/~지/~어 같은 구어체 사용.
  독자는 "정말?", "엥?", "그게 뭔데", "그래서?" 같이 짧고 솔직하게.
  ✅ 올바른 예:
    {BLOG_NAME}: 그런 경우가 생각보다 많아.
    독자: 정말?
    {BLOG_NAME}: 정확해. 그래서 다들 놀라는 거지.
  ❌ 금지: ~입니다, ~습니다, ~이다, ~한다 (딱딱한 말투 금지)
- 출력 형식 (반드시 이 대로):
[CHAT]
{BLOG_NAME}: (설명하는 말)
독자: (짧은 반응이나 질문)
{BLOG_NAME}: (이어지는 설명)
독자: (추가 반응)
{BLOG_NAME}: (마무리 설명)
[/CHAT]"""
    else:
        chat_instruction = "# [대화 구간 없음] 이 글은 대화 형식 없이 본문만으로 구성한다."

    topic_prompt = TOPIC_PROMPT[trivia_type]

    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    prompt = f"""아래 조건에 맞는 잡학 블로그 글을 써라.

{topic_prompt}

[금지 주제 - 최근 사용됨, 의미상 비슷한 것도 피할 것]
{avoid_str}

[SEO 최적화 — 글 쓰기 전에 포커스 키워드(2~4단어)를 먼저 정하고, 아래 5곳에 반드시 포함한다]
  ① 제목(# H1): 키워드를 제목 앞쪽에 자연스럽게 배치
  ② 첫 문단 100자 이내: 키워드 또는 동일 표현이 첫 문단 앞부분에 등장
  ③ ## 대제목 최소 1개: 키워드 또는 근접 변형어 포함
  ④ SEO_TITLE: 키워드로 시작하거나 앞쪽 3단어 이내 배치
  ⑤ SEO_DESCRIPTION 첫 문장: 키워드 포함
- 키워드 밀도: 전체 본문의 1~2% (자연스럽게 분산, 억지 반복 금지)

[모바일 최적화 — 가독성 필수 조건]
- 문단 길이: 2~3문장이면 반드시 줄 바꿈. 스마트폰 화면에서 한 문단이 5줄을 넘으면 안 된다.
- 문장 길이: 한 문장에 50자 이내. 길어지면 둘로 쪼갠다.
- 3개 이상 나열: 반드시 리스트(- ) 형식. 문장 안에 쉼표로 나열 금지.
- 굵게(**bold**)로 핵심 정보를 부각 — 스캐닝하는 독자가 굵은 글씨만 읽어도 핵심을 알 수 있어야 함.
- 텍스트 덩어리(벽돌 텍스트) 절대 금지. 줄 바꿈·리스트·대제목으로 여백을 만든다.

[형식 조건]
- 분량: 700단어 이상 (한국어 약 2800자 이상). 할 말 있어서 길어지는 글. 억지 패딩 금지.
- 제목(#): "왜 ~일까?", "~의 진짜 이유", "사실 ~였다" 등 호기심 자극 형식.
- 대제목(##): 반드시 **굵게(bold)**. 2개·3개·4개 중 하나를 매번 다르게 선택해서 사용한다.
- 소제목(###), 이모지, 리스트(-): 내용에 맞게 적절히.
- 굵게(**bold**): 핵심 키워드·수치·결론 문장에 1~2개/문단.
- 하이라이트(<mark>): 꼭 기억할 핵심 문구 1~2곳.
- 전문용어 첫 등장 시 괄호로 쉬운 설명 추가.
- 문체: 친근한 평어체. ~다/~이다/~한다. ❌ ~습니다/~요/~죠 금지.

[외부 링크 - 본문에 반드시 2~3개 삽입]
형식: <a href="https://실제URL" target="_blank">앵커텍스트</a>
신뢰도 순서: 대형 언론사·공공기관 > 유명 전문 사이트 > 나무위키·위키백과
추천 소스 (주제에 맞게 선택):
- 한국어 위키백과 (ko.wikipedia.org): 개념 설명이 필요한 용어·현상에
- 나무위키 (namu.wiki): 친근한 설명이 필요할 때
- 사이언스타임즈 (sciencetimes.co.kr): 과학 관련 주제
- YTN 사이언스 (science.ytn.co.kr): 과학·자연 관련
- 국립중앙과학관 (science.go.kr): 과학 개념 설명
- 네이버 지식백과 (terms.naver.com): 백과사전 항목
- 조선일보·중앙일보·한국경제 등 대형 언론사 관련 기사
주의:
  ✅ 반드시 내용과 직접 관련된 하위 페이지·기사 URL 사용 (홈페이지 루트 금지)
  ✅ 앵커텍스트는 URL이 아닌 자연스러운 한국어 문구로
  ❌ 존재하지 않을 것 같은 URL 지어내지 말 것 — 확실한 URL만 사용

[유머 - 글 전체에 1~2곳, 자연스럽게]
- 억지로 넣지 않는다. 맥락이 맞을 때만. 없으면 안 넣어도 된다.
- 허용되는 유머: 가벼운 말장난·언어유희, 공감되는 자조적 표현("이거 나만 몰랐나?", "알고 나니 더 억울하다"),
  요즘 인터넷 밈 뉘앙스("~인데요?", "이거 실화임?", "소름 돋았으면 손 들어"), 과장된 리액션.
- 금지: 특정 집단·인물 비하, 억지 개그, 콘텐츠 흐름을 끊는 유머.
- 유머 위치: 도입부 첫 문장, 대화 구간, 마무리 중 자연스러운 곳 1~2군데면 충분하다.

{chat_instruction}

[내용 구성]
{structure}

---
글 본문이 끝나면 반드시 아래 5줄 출력. 절대 빠뜨리지 말 것.
FOCUS_KEYWORD: 핵심 검색어(2~4단어)
SEO_TITLE: SEO 제목(60자 이내, 포커스 키워드 앞쪽)
SEO_DESCRIPTION: 메타 설명(150~160자, 포커스 키워드 포함, 클릭 유도)
IMAGE_QUERY: 글 핵심 장면 영어 3~5단어 (구체적 사물/장면, 추상어 금지)
  예) 하늘 파란색 → "blue sky sunlight scattering atmosphere"
      하품 전염 → "person yawning tired face closeup"
TAGS: 태그1,태그2,태그3,태그4,태그5"""

    print("  Claude API 호출 중 (잡학)...")
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

    # 이미지
    image_query = result.get('image_query', 'curious science nature fact')
    print(f"  이미지 검색: {image_query}")
    featured_image = fetch_featured_image(image_query)
    body_images    = fetch_multiple_images(image_query, count=3)

    if featured_image:
        print(f"  대표 이미지: {featured_image['credit']}")
    if body_images:
        print(f"  본문 이미지: {len(body_images)}장")

    # WordPress 발행 (항상 임시글)
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
        topic=f'잡학({trivia_type})',
        site='health_trivia',
    )

    print(f"  ✅ [{trivia_type} 잡학] 임시글 저장 완료! ID: {post_result['id']} / {post_result['url']}")
    return post_result


if __name__ == '__main__':
    post_trivia()
