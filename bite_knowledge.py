"""
bite_knowledge.py - '한 입 지식' 카테고리 단편 경제 용어 포스팅
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import re
import anthropic
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
load_dotenv()

from images import fetch_multiple_images
from wordpress import upload_image_from_url
from topic_tracker import get_recent_keywords, save_topic

CATEGORY_ID = 37  # 한 입 지식


def post_bite_knowledge():
    used = get_recent_keywords(days=45, site='economy')
    avoid_str = ', '.join(used[-30:]) if used else '없음'

    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    prompt = f"""경제/금융/부동산/투자 관련 용어 중 하나를 골라 아래 형식으로 써라.

[금지 단어 - 이미 사용됨, 절대 중복 금지]
{avoid_str}

[선택 기준]
- 일반인이 뉴스에서 접하지만 정확히 모를 법한 용어
- 실생활 재테크와 연관된 용어 우선
- 위 금지 단어와 의미상 비슷한 것도 피할 것

[본문 조건]
- 280자 이내 한국어
- 전문용어 없이 중학생도 이해할 수 있게
- 실생활 예시나 비유 반드시 포함
- 마지막 문장은 "한 줄 요약: ~" 형식으로 마무리

출력 형식 (반드시 이 순서로):
본문 내용 먼저 작성

TITLE: 용어명
IMAGE_QUERY: english 2-3 words
TAGS: 태그1,태그2,태그3,태그4"""

    print("  Claude API 호출 중 (한 입 지식)...")
    msg = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}]
    )
    raw = msg.content[0].text

    def extract(pattern):
        m = re.search(pattern, raw, re.MULTILINE)
        return m.group(1).strip() if m else ''

    term_title  = extract(r'^TITLE:\s*(.+)$')
    image_query = extract(r'^IMAGE_QUERY:\s*(.+)$')
    tags_raw    = extract(r'^TAGS:\s*(.+)$')
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

    # 본문: 메타 줄 제거
    body = re.sub(r'^(TITLE|IMAGE_QUERY|TAGS):.*$', '', raw, flags=re.MULTILINE).strip()
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    body_html = '\n'.join(f'<p>{p}</p>' for p in paragraphs)
    if tags:
        body_html += '\n<p style="margin-top:1.2em;font-size:0.85em;color:#aaa;">' \
                     + ' '.join(f'#{t}' for t in tags) + '</p>'

    # 한 입 지식 전용 헤더 (레이블 + H2 제목)
    content_html = (
        f'<p style="font-size:1em;font-weight:700;color:#F41414;margin-bottom:6px;">💡 오늘의 경제 용어</p>\n'
        f'<h1>{term_title}</h1>\n'
        + body_html
    )

    print(f"  용어: {term_title} / {len(body)}자")

    # 이미지
    imgs = fetch_multiple_images(image_query or 'finance money economy', count=1)
    featured_url = imgs[0]['url'] if imgs else None

    # WP 설정
    wp_env = {
        'wp_url_env':  'WP2_URL',
        'wp_user_env': 'WP2_USER',
        'wp_pass_env': 'WP2_APP_PASSWORD',
    }
    wp_url_base = os.environ.get('WP2_URL', '').rstrip('/')
    auth = HTTPBasicAuth(os.environ.get('WP2_USER', ''), os.environ.get('WP2_APP_PASSWORD', ''))

    # 태그 ID 변환
    tag_ids = []
    for name in tags:
        r = requests.get(f'{wp_url_base}/wp-json/wp/v2/tags',
                         params={'search': name, 'per_page': 5}, auth=auth, timeout=10)
        matched = next((t for t in (r.json() if r.ok else []) if t['name'] == name), None)
        if matched:
            tag_ids.append(matched['id'])
        else:
            cr = requests.post(f'{wp_url_base}/wp-json/wp/v2/tags',
                               json={'name': name}, auth=auth, timeout=10)
            if cr.ok:
                tag_ids.append(cr.json()['id'])

    # 대표 이미지 업로드
    featured_media_id = None
    if featured_url:
        featured_media_id, _ = upload_image_from_url(
            featured_url, term_title, wp_env=wp_env,
            alt_text=f'{term_title} 이미지',
            caption_kr='이미지 출처: Pixabay',
        )

    # 포스트 발행
    post_data = {
        'title':      term_title,
        'content':    content_html,
        'status':     'draft',
        'categories': [CATEGORY_ID],
        'tags':       tag_ids,
    }
    if featured_media_id:
        post_data['featured_media'] = featured_media_id

    resp = requests.post(f'{wp_url_base}/wp-json/wp/v2/posts',
                         json=post_data, auth=auth, timeout=30)
    if resp.ok:
        data = resp.json()
        print(f"  ✅ 한 입 지식 발행 완료! ID: {data['id']} / {data['link']}")
        save_topic(keyword=term_title, title=term_title, topic='한 입 지식', site='economy')
    else:
        print(f"  ❌ 발행 실패: {resp.status_code} {resp.text[:200]}")


if __name__ == '__main__':
    post_bite_knowledge()
