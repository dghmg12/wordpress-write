"""
writer.py - Claude API를 이용한 글 작성 모듈
"""
import anthropic
import os
import re
import random
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def get_client():
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def write_article(articles: list[dict], topic: str = "", used_keywords: list[str] = None,
                  style_hint: str = "", style_desc: str = "", link_sources: list = None,
                  site_label: str = "", blog_name: str = "블로그") -> dict:
    """
    수집된 기사들을 바탕으로 Claude API로 블로그 글 생성

    Args:
        articles: 크롤러에서 가져온 기사 목록
        topic: 강제 지정 주제 (없으면 기사 내용 기반으로 자동 결정)

    Returns:
        {"title": str, "content_html": str, "excerpt": str, "tags": list}
    """
    client = get_client()

    today = datetime.now(KST)
    date_str = today.strftime("%Y년 %m월 %d일")

    # 기사 요약본 조립 (출처 URL 포함)
    articles_text = ""
    for i, a in enumerate(articles[:5], 1):  # 최대 5개 기사 참고
        articles_text += f"\n[기사 {i}]\n제목: {a['title']}\n출처: {a['source']}\nURL: {a.get('url', '')}\n내용: {a['summary']}\n"

    topic_instruction = f"주제는 [{topic}]이며, " if topic else ""
    style_instruction = f"이 블로그는 [{style_desc}] 콘텐츠를 다룬다." if style_desc else ""

    # 도입부 스타일 랜덤 선택 (글마다 다른 시작)
    intro_styles = [
        "나 자신의 직접 경험담으로 시작한다 (\"나는\", \"솔직히 말하면\", \"직접 해봤는데\" 등 1인칭 서술). 단, 모든 글이 이 패턴이면 안 되니 자연스럽게 변형한다.",
        "독자에게 직접 질문을 던지며 공감을 끌어내는 방식으로 시작한다 (\"혹시 이런 경험 있어?\", \"한 번쯤은 들어봤을 거다\", \"이거 제대로 아는 사람 얼마나 될까\" 등).",
        "주변 지인이나 실제 사례로 시작한다 (\"얼마 전 친구가\", \"주변에서 흔히 보이는\", \"아는 분이 이런 얘기를 하더라\" 등). 경험을 간접적으로 풀어낸다.",
        "의외의 사실이나 반전 정보로 시작한다 (\"사실 이거 아는 사람 드물어\", \"~인 줄 알았는데 완전 반대였다\", \"이 숫자 보면 놀랄 수도 있다\" 등). 흥미를 유발한다.",
    ]
    intro_style = random.choice(intro_styles)

    # 글 구성 패턴 랜덤 선택 (H2 개수·흐름 다양화)
    structure_patterns = [
        """\
[내용 구성 - 패턴A: 2단 핵심+실전]
1. 도입부 (3~4문장): {intro} 포커스 키워드 포함.
2. ## **[핵심 정보 또는 놀라운 사실 제목]**
   의외의 사실·데이터·근거 중심으로 충분히 길게 쓴다. 독자가 "몰랐다" 싶은 내용.
3. ## **[오늘 당장 써먹을 실전 제목]**
   구체적 행동, 체크리스트, 단계별 방법. ### 소제목이나 리스트 적극 활용.
4. 마무리 (3~4문장): 핵심 한 줄 정리 + 독자 행동 유도.""",

        """\
[내용 구성 - 패턴B: 2단 오해+반전]
1. 도입부 (3~4문장): {intro} 포커스 키워드 포함.
2. ## **[흔한 오해 또는 잘못된 상식 제목]**
   대부분의 사람이 당연하게 여기는 것, 하지만 사실은 틀렸거나 불완전한 부분 파헤치기.
3. ## **[진짜 방법 또는 반전 제목]**
   앞 단의 오해를 뒤집는 올바른 정보. 구체적 근거와 실전 적용법 포함.
4. 마무리 (3~4문장): 핵심 정리 + 독자가 내일부터 바꿔볼 한 가지 제안.""",

        """\
[내용 구성 - 패턴C: 3단 배경+핵심+실전]
1. 도입부 (3~4문장): {intro} 포커스 키워드 포함.
2. ## **[왜 이게 중요한지·배경 제목]**
   이 주제가 지금 왜 뜨는지, 어떤 상황에서 문제가 생기는지 배경과 맥락 설명.
3. ## **[핵심 정보·해결책 제목]**
   구체적 수치·방법·데이터 중심. 이 글에서 가장 알차고 긴 파트.
4. ## **[실전 적용·나의 선택 제목]**
   독자 상황에 바로 적용할 수 있는 내용. ### 소제목이나 리스트 활용.
5. 마무리 (2~3문장): 짧고 강렬한 한 줄 결론.""",

        """\
[내용 구성 - 패턴D: 3단 스토리형]
1. 도입부 (3~4문장): {intro} 포커스 키워드 포함.
2. ## **[계기 또는 문제 상황 제목]**
   처음 이 주제를 접하게 된 상황, 또는 많은 사람들이 공통으로 겪는 불편·의문 서술.
3. ## **[발견한 사실 또는 전환점 제목]**
   직접 해보거나 알게 된 핵심 정보. "이렇게 다를 줄 몰랐다"는 반전 포함.
4. ## **[그래서 어떻게 달라졌나·결론 제목]**
   변화된 내용, 독자에게 주는 시사점. 구체적 숫자나 비교 포함하면 더 좋다.
5. 마무리 (2~3문장): 공감을 끌어내는 마무리 + 댓글·공유 유도.""",

        """\
[내용 구성 - 패턴E: 4단 심층 분석형]
1. 도입부 (3~4문장): {intro} 포커스 키워드 포함.
2. ## **[왜 지금 이게 중요한가]**
   이 주제가 현재 화제인 이유, 독자 삶과의 연결고리.
3. ## **[핵심 정보 1 — 사실과 근거]**
   가장 알차고 긴 파트. 데이터·수치·비교 중심.
4. ## **[핵심 정보 2 — 실전 적용 또는 반전]**
   앞 단의 내용을 한 단계 더 발전시키거나, 독자가 바로 써먹을 수 있는 내용.
5. ## **[정리 — 내가 내린 결론]**
   글 전체를 아우르는 내 시각과 한 줄 결론.
6. 마무리 (2문장): 짧고 강렬하게.""",

        """\
[내용 구성 - 패턴F: 4단 Q&A 확장형]
1. 도입부 (3~4문장): {intro} 포커스 키워드 포함.
2. ## **[많은 사람들이 궁금해하는 것]**
   이 주제에서 사람들이 가장 자주 묻는 질문 2~3가지를 꺼낸다. ### 소제목으로 각각 답변.
3. ## **[실제로 해보니 달랐던 점]**
   직접 경험 또는 실증 데이터 기반. "이론과 현실의 차이"를 보여준다.
4. ## **[놓치기 쉬운 함정]**
   많은 사람이 실수하는 포인트, 주의사항. 리스트(-) 활용.
5. ## **[결국 핵심은 이것]**
   글 전체를 한 문장으로 압축. 독자가 기억해야 할 딱 하나의 메시지.
6. 마무리 (2~3문장): 독자 행동 유도.""",
    ]
    structure_pattern = random.choice(structure_patterns).replace("{intro}", intro_style)

    # 대화 구간 랜덤 포함 여부 (50%)
    use_chat = random.random() < 0.5
    if use_chat:
        chat_instruction = f"""\
[대화 구간 - 어려운 내용 쉽게 풀기]
- 글 중간 내용이 어려워지는 지점에서 아래 형식의 대화 블록을 정확히 1개 삽입한다.
- 대화는 3~5번 주고받는다.
- 말투: 친한 친구끼리 편하게 얘기하는 느낌. 짧고 자연스럽게.
  {blog_name}은 ~야/~거야/~잖아/~지/~어 같은 구어체 사용.
  독자는 "정말?", "엥?", "그게 뭔데", "그래서?" 같이 짧고 솔직하게.
  ✅ 올바른 예:
    {blog_name}: 그런 경우가 생각보다 많아.
    독자: 정말?
    {blog_name}: 정확해. 그러니까 수천만원을 날리는 거지.
  ❌ 금지: ~입니다, ~습니다, ~이다, ~한다 (딱딱한 말투 금지)
- 출력 형식 (반드시 이 대로):
[CHAT]
{blog_name}: (설명하는 말)
독자: (짧은 반응이나 질문)
{blog_name}: (이어지는 설명)
독자: (추가 반응)
{blog_name}: (마무리 설명)
[/CHAT]"""
    else:
        chat_instruction = "# [대화 구간 없음] 이 글은 대화 형식 없이 본문만으로 구성한다."

    # 인라인 링크: 실제 크롤링된 기사 URL 우선 사용
    article_urls = [(a['title'], a.get('url', '')) for a in articles[:5] if a.get('url', '')]
    if article_urls:
        url_list = "\n".join([f'  - {title}: {url}' for title, url in article_urls])
        link_instruction = (
            f"\n- 본문 내에서 자연스러운 키워드나 문장에 아래 기사 URL 중 내용과 가장 관련 있는 2~3개를 골라 "
            f"<a href=\"URL\" target=\"_blank\">앵커텍스트</a> 형식으로 삽입한다. "
            f"메인 홈페이지가 아닌 반드시 아래의 실제 기사 URL을 그대로 사용한다:\n{url_list}"
        )
    elif link_sources:
        link_instruction = (
            "\n- 본문 내에서 자연스러운 키워드나 문장에 신뢰할 수 있는 관련 링크를 2~3개 삽입한다. "
            "반드시 홈페이지 메인이 아닌, 내용과 직접 관련 있는 하위 페이지나 문서 URL을 사용한다."
        )
    else:
        link_instruction = "\n- 본문 내에서 신뢰할 수 있는 외부 링크를 2~3개 자연스럽게 삽입한다."

    # 최근 사용 키워드 중복 방지 문구
    if used_keywords:
        avoid_list = ", ".join(used_keywords[-20:])  # 최근 20개
        avoid_instruction = f"\n\n[중복 금지 - 아래 키워드와 비슷한 주제는 절대 쓰지 않는다]\n{avoid_list}\n→ 위 키워드와 겹치지 않는 완전히 새로운 각도와 소재를 골라라."
    else:
        avoid_instruction = ""

    prompt = f"""오늘은 {date_str}이다. {style_instruction} {topic_instruction}아래 참고자료(뉴스·커뮤니티)는 트렌드와 실제 사람들의 경험을 파악하는 용도로만 본다. 내용을 직접 인용하거나 복사하지 않는다.{avoid_instruction}

---참고자료 (뉴스 + 커뮤니티 경험담 — 내용 복사 금지)---
{articles_text}
---------------

[핵심 원칙 - 가장 중요]
- 참고자료를 "베끼는" 것이 아니라, 키워드·트렌드·실제 경험 패턴만 파악하고 완전히 새로운 내 글을 쓴다.
- 커뮤니티 글(출처에 "[커뮤니티]"가 붙은 것)에서는 실제 사람들이 겪은 상황, 고민, 반응 패턴을 참고한다.
  단, 특정 아이디나 개인정보는 절대 언급하지 않는다. 일반화해서 "많은 사람들이 이런 경험을 한다"는 식으로 녹인다.
- 뉴스에 나온 특정 인물·사건·수치를 그대로 가져오지 않는다.
- 글의 각도(앵글)를 내가 직접 잡는다. 같은 주제라도 참고자료와 다른 시각, 다른 결론으로 이끌어야 한다.

[블로그 성격]
- 친근하고 솔직한 글투로 쓴다. 전문가 강의체가 아니라, 옆자리 사람이 경험을 털어놓듯이.
- 커뮤니티에서 실제로 나오는 "이런 경험 있어?", "나는 이렇게 했더니" 같은 생생한 뉘앙스를 글 전체에 자연스럽게 녹인다.
- 흔히 알려진 상식을 뒤집거나, 의외의 사실을 꺼내거나, "나만 몰랐나?" 싶은 정보를 중심으로 구성한다.
- 독자가 읽고 나서 "오, 나도 해봐야겠다" 또는 "그래서 그랬구나" 반응이 나오게 써라.

[유머 - 글 전체에 1~2곳, 자연스럽게]
- 억지로 넣지 않는다. 맥락이 맞을 때만. 없으면 안 넣어도 된다.
- 허용되는 유머: 가벼운 말장난·언어유희, 공감되는 자조적 표현("이거 나만 몰랐나?", "알고 나니 더 억울하다"),
  요즘 인터넷 밈 뉘앙스("~인데요?", "이거 실화임?", "소름 돋았으면 손 들어"), 과장된 리액션.
- 금지: 특정 집단·인물 비하, 억지 개그, 콘텐츠 흐름을 끊는 유머.
- 유머 위치: 도입부 첫 문장, 대화 구간, 마무리 중 자연스러운 곳 1~2군데면 충분하다.

[형식 조건]
- 전체 분량: 700단어 이상 (영어 단어 기준, 한국어로 약 2800자 이상).
  단, 분량을 채우려고 억지로 문장을 늘리지 않는다. 할 말이 있어서 길어지는 글을 써라.
  "또한", "이처럼", "따라서" 같은 연결어로 문장을 이어 붙이거나, 앞에서 한 말을 살짝 바꿔 반복하는 패딩은 절대 금지.
- 제목: # 형식, 클릭하고 싶어지는 제목 (숫자, 반전, 질문 형식 활용).
- 대제목(##): **반드시 굵게(bold)**. 2개·3개·4개 중 하나를 매번 다르게 선택해서 사용한다. 예: ## **이게 진짜 핵심이다**
- 소제목(###): 내용이 세부 항목으로 나뉠 때 맥락에 맞게 사용한다.
- 이모지: 소제목이나 강조 문장 앞에 맥락에 맞는 이모지를 적절히 사용한다 (과하지 않게, 2~4개).
- 리스트(-): 비교·체크리스트·단계별 항목처럼 나열이 자연스러운 경우에 사용한다. 단순 정보 나열에는 쓰지 않는다.
- 굵게(**bold**): 각 문단에서 핵심 키워드나 중요한 수치/결론 문장에 1~2개 적용한다.
- 하이라이트(<mark>): 독자가 반드시 기억해야 할 핵심 문구 1~2곳에 <mark>문구</mark> 형식으로 적용한다.
- 문체: 반드시 평어체로만 쓴다. 글 전체에서 단 한 문장도 예외 없이 ~다/~이다/~한다/~았다로 끝낸다.
  ❌ 절대 금지: ~습니다, ~입니다, ~합니다, ~세요, ~요, ~죠, ~군요, ~네요
  ✅ 올바른 예: "이게 진짜 핵심이다.", "직접 해봤는데 달랐다.", "모르는 사람이 더 많다."
- 각 문단은 3~5문장으로 쓴다. 할 말이 있으면 길어도 되고, 짧아도 된다. 억지로 채우지 않는다.
- 전문용어·영어 단어가 처음 등장할 때는 바로 뒤에 괄호로 1줄 이내 쉬운 설명을 덧붙인다.
  예: "ETF(여러 주식을 한 바구니에 담아 거래소에서 사고파는 펀드)", "LDL 콜레스테롤(혈관 벽에 쌓이는 나쁜 콜레스테롤)"처럼.
  단, 누구나 아는 단어(혈압, 단백질, 금리 등)는 설명 생략.

{chat_instruction}

{structure_pattern}

[출처 표기 - 반드시 포함]
- 글 맨 아래에 오늘 트렌드를 파악하는 데 참고한 뉴스 출처를 아래 형식으로 가볍게 표기한다:
  <p style="font-size:0.85em;color:#999;margin-top:2em;">📰 오늘의 {site_label or "뉴스"} 참고: <a href="실제기사URL" target="_blank">출처명</a>, <a href="실제기사URL" target="_blank">출처명</a></p>
- 기사를 직접 인용한 게 아니므로 "참고 자료"가 아니라 "오늘의 뉴스 참고"로 표기한다.
- 반드시 실제 기사 URL(위 트렌드 참고 섹션의 URL)과 출처명을 사용한다. 홈페이지 주소 금지.

[Rank Math SEO - 반드시 준수]
- 포커스 키워드를 제목(#), 도입부, ## 대제목 1개에 포함.
- 포커스 키워드 밀도 1~2% 유지.
- 외부 링크: 본문에 **반드시 2~3개** 삽입. <a href="https://..." target="_blank">앵커텍스트</a> 형식.
  신뢰도 순서: 대형 언론사(조선·중앙·한경·연합뉴스 등) > 공공기관 > 유명 전문 사이트 > 나무위키/위키백과.
  홈페이지 루트(예: naver.com) 금지 — 반드시 내용과 직접 관련된 기사·문서·하위 페이지 URL 사용.
  앵커텍스트는 URL이 아닌 자연스러운 한국어 문구로.{link_instruction}

---
글 본문이 끝나면 반드시 아래 6줄을 출력한다. 절대 빠뜨리지 말 것.
FOCUS_KEYWORD: 포커스키워드(2~4단어, 핵심 검색어 하나만)
SEO_TITLE: SEO 최적화 제목(60자 이내, 포커스 키워드 앞쪽 배치)
SEO_DESCRIPTION: 메타 설명(150~160자, 포커스 키워드 포함, 클릭 유도 문장)
IMAGE_QUERY: 글 핵심 장면을 시각적으로 표현하는 영어 3~5단어. 추상어 금지, Pexels/Pixabay에서 실제로 검색 가능한 구체적 사물·행동·장면으로.
  예) 운동 루틴 글 → "person morning workout routine stretch"
      식단 관리 글 → "healthy meal prep vegetables bowl"
      부동산 투자 글 → "apartment building investment real estate"
      금리 인상 글 → "bank interest rate financial graph"
TAGS: 태그1,태그2,태그3,태그4,태그5
EXCERPT: 150자 이내 한국어 발췌문"""

    print("  Claude API 호출 중...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    return parse_output(raw, blog_name=blog_name)


def parse_output(raw: str, blog_name: str = "블로그") -> dict:
    """Claude 출력에서 제목, 본문, 태그, 발췌문, SEO 필드 분리"""

    def extract(pattern):
        m = re.search(pattern, raw, re.MULTILINE)
        return m.group(1).strip() if m else ""

    # 메타 필드 추출
    tags_raw     = extract(r"^TAGS:\s*(.+)$")
    excerpt      = extract(r"^EXCERPT:\s*(.+)$")
    focus_kw     = extract(r"^FOCUS_KEYWORD:\s*(.+)$")
    seo_title    = extract(r"^SEO_TITLE:\s*(.+)$")
    seo_desc     = extract(r"^SEO_DESCRIPTION:\s*(.+)$")
    image_query  = extract(r"^IMAGE_QUERY:\s*(.+)$")

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    # 메타 줄 전부 제거
    body = re.sub(
        r"^(TAGS|EXCERPT|FOCUS_KEYWORD|SEO_TITLE|SEO_DESCRIPTION|IMAGE_QUERY):.*$",
        "",
        raw,
        flags=re.MULTILINE,
    ).strip()

    # 제목 추출
    title = "자동 생성 포스트"
    for line in body.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Markdown → HTML 변환 ([CHAT] 블록 포함)
    content_html = markdown_to_html(body, blog_name=blog_name)

    return {
        "title": title,
        "content_html": content_html,
        "content_markdown": body,
        "excerpt": excerpt,
        "tags": tags,
        # SEO / Rank Math 필드
        "focus_keyword": focus_kw,
        "seo_title": seo_title or title,
        "seo_description": seo_desc or excerpt,
        "image_query": image_query or focus_kw or title[:30],
    }


def markdown_to_html(text: str, blog_name: str = "블로그") -> str:
    """
    Markdown → WordPress Gutenberg 블록 형식 HTML 변환.
    [CHAT]...[/CHAT] 블록은 말풍선 대화 형식으로 변환.
    """
    # [CHAT] 블록 분리 → 각각 다르게 처리
    segments = re.split(r'(\[CHAT\].*?\[/CHAT\])', text, flags=re.DOTALL)

    all_blocks = []
    for seg in segments:
        if seg.startswith('[CHAT]') and '[/CHAT]' in seg:
            inner = seg[6:seg.index('[/CHAT]')].strip()
            chat_html = _chat_to_html(inner, blog_name)
            if chat_html:
                all_blocks.append(f'<!-- wp:html -->\n{chat_html}\n<!-- /wp:html -->')
        elif seg.strip():
            all_blocks.extend(_process_markdown_lines(seg))

    return "\n\n".join(all_blocks)


def _chat_to_html(chat_text: str, blog_name: str = "블로그") -> str:
    """[CHAT] 블록 내용을 말풍선 HTML로 변환.
    blog_name 발화는 왼쪽(흰 말풍선), 독자 발화는 오른쪽(회색 말풍선).
    blog_name 글자만 빨간색으로 강조.
    """
    lines = [l.strip() for l in chat_text.split('\n') if l.strip()]
    msgs = []
    for line in lines:
        if ':' not in line:
            continue
        speaker, _, content = line.partition(':')
        speaker = speaker.strip()
        content = content.strip()
        role = 'blog' if speaker == blog_name else 'reader'
        msgs.append((role, speaker, content))

    if not msgs:
        return ''

    rows = []
    for i, (role, speaker, content) in enumerate(msgs):
        mb = 'margin-bottom:12px;' if i < len(msgs) - 1 else ''
        if role == 'blog':
            rows.append(
                f'<div style="{mb}display:flex;align-items:flex-start;">'
                f'<div style="max-width:85%;">'
                f'<div style="font-size:.75em;font-weight:700;color:#F41414;margin-bottom:3px;">{speaker}</div>'
                f'<div style="background:#fff;border:1px solid #e5e5e5;'
                f'border-radius:4px 16px 16px 16px;padding:10px 14px;'
                f'color:#333;font-size:.95em;line-height:1.65;">{content}</div>'
                f'</div>'
                f'</div>'
            )
        else:
            rows.append(
                f'<div style="{mb}display:flex;justify-content:flex-end;">'
                f'<div style="max-width:85%;text-align:right;">'
                f'<div style="font-size:.75em;font-weight:600;color:#aaa;margin-bottom:3px;">{speaker}</div>'
                f'<div style="background:#f0f0f0;border-radius:16px 4px 16px 16px;'
                f'padding:10px 14px;color:#333;font-size:.95em;line-height:1.65;">{content}</div>'
                f'</div>'
                f'</div>'
            )

    inner_html = '\n'.join(rows)
    return (
        f'<div style="margin:2em 0;padding:18px 20px;background:#f9f9f9;'
        f'border-radius:16px;border:1px solid #F41414;">\n'
        f'{inner_html}\n'
        f'</div>'
    )


def _process_markdown_lines(text: str) -> list:
    """마크다운 텍스트 → Gutenberg 블록 리스트 변환 (markdown_to_html 내부용)"""
    lines = text.split("\n")
    blocks = []
    in_list = False
    list_items = []

    def close_list():
        nonlocal in_list
        if list_items:
            items_html = "".join(
                f"\n<!-- wp:list-item --><li>{item}</li><!-- /wp:list-item -->"
                for item in list_items
            )
            blocks.append(
                f'<!-- wp:list -->\n<ul class="wp-block-list">{items_html}\n</ul>\n<!-- /wp:list -->'
            )
            list_items.clear()
        in_list = False

    for line in lines:
        is_list_item = line.startswith("- ") or line.startswith("* ")

        if not is_list_item and in_list:
            close_list()

        if line.startswith("# "):
            pass  # 포스트 제목은 WordPress가 H1로 출력 → 본문엔 생략

        elif line.startswith("## "):
            raw = line[3:].strip()
            inner = apply_inline(raw)
            if not inner.startswith("<strong>"):
                inner = f"<strong>{inner}</strong>"
            blocks.append(
                f'<!-- wp:heading {{"level":2}} -->\n'
                f'<h2 class="wp-block-heading">{inner}</h2>\n'
                f'<!-- /wp:heading -->'
            )

        elif line.startswith("### "):
            raw = line[4:].strip()
            blocks.append(
                f'<!-- wp:heading {{"level":3}} -->\n'
                f'<h3 class="wp-block-heading">{apply_inline(raw)}</h3>\n'
                f'<!-- /wp:heading -->'
            )

        elif is_list_item:
            in_list = True
            list_items.append(apply_inline(line[2:].strip()))

        elif line.strip() == "":
            pass

        elif line.strip().startswith("<"):
            blocks.append(f'<!-- wp:html -->\n{line.strip()}\n<!-- /wp:html -->')

        else:
            blocks.append(
                f'<!-- wp:paragraph -->\n'
                f'<p>{apply_inline(line)}</p>\n'
                f'<!-- /wp:paragraph -->'
            )

    if in_list:
        close_list()

    return blocks


def apply_inline(text: str) -> str:
    """굵게, 기울임 처리"""
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
    return text


if __name__ == "__main__":
    # 테스트 실행
    from dotenv import load_dotenv
    load_dotenv()

    dummy_articles = [
        {"title": "한국 부동산 시장 전망", "source": "테스트", "summary": "올해 부동산 시장이 안정세를 보이고 있다."},
        {"title": "서울 아파트 가격 동향", "source": "테스트", "summary": "서울 아파트 가격이 소폭 하락했다."},
    ]

    print("=== 글 작성 테스트 ===")
    result = write_article(dummy_articles, topic="부동산")
    print(f"제목: {result['title']}")
    print(f"태그: {result['tags']}")
    print(f"발췌: {result['excerpt']}")
    print(f"본문 길이: {len(result['content_markdown'])}자")
