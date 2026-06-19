"""
wordpress.py - WordPress REST API 연동 모듈
"""
import requests
import os
import json
from requests.auth import HTTPBasicAuth


def get_wp_config(url_env="WP_URL", user_env="WP_USER", pass_env="WP_APP_PASSWORD"):
    """환경변수에서 WordPress 설정 읽기 (멀티 사이트 지원)"""
    url = os.environ.get(url_env, "").rstrip("/")
    user = os.environ.get(user_env, "")
    app_password = os.environ.get(pass_env, "")

    if not url or not user or not app_password:
        raise ValueError(
            f"WordPress 설정이 없습니다. .env 파일에 {url_env}, {user_env}, {pass_env}를 입력하세요."
        )
    return url, user, app_password


def get_or_create_tags(tag_names: list[str], wp_env: dict = None) -> list[int]:
    """
    태그 이름 목록 → WordPress 태그 ID 목록 반환
    없으면 자동 생성
    """
    if not tag_names:
        return []

    wp_env = wp_env or {}
    url, user, app_password = get_wp_config(
        wp_env.get("wp_url_env", "WP_URL"),
        wp_env.get("wp_user_env", "WP_USER"),
        wp_env.get("wp_pass_env", "WP_APP_PASSWORD"),
    )
    auth = HTTPBasicAuth(user, app_password)
    tag_ids = []

    for name in tag_names:
        # 먼저 검색
        resp = requests.get(
            f"{url}/wp-json/wp/v2/tags",
            params={"search": name, "per_page": 5},
            auth=auth,
            timeout=10,
        )
        tags = resp.json() if resp.ok else []
        matched = next((t for t in tags if t["name"] == name), None)

        if matched:
            tag_ids.append(matched["id"])
        else:
            # 없으면 생성
            create_resp = requests.post(
                f"{url}/wp-json/wp/v2/tags",
                json={"name": name},
                auth=auth,
                timeout=10,
            )
            if create_resp.ok:
                tag_ids.append(create_resp.json()["id"])
            else:
                print(f"  ⚠ 태그 생성 실패: {name}")

    return tag_ids


def publish_post(
    title: str,
    content_html: str,
    excerpt: str = "",
    tags: list[str] = None,
    category_id: int = None,
    status: str = None,
    featured_image_url: str = None,
    image_list: list[dict] = None,
    # Rank Math SEO 필드
    focus_keyword: str = "",
    seo_title: str = "",
    seo_description: str = "",
    image_alt: str = "",
    # 멀티 사이트
    wp_env: dict = None,
) -> dict:
    """
    WordPress에 포스트 발행

    Args:
        title: 포스트 제목
        content_html: HTML 본문
        excerpt: 발췌문 (메타 설명)
        tags: 태그 이름 목록
        category_id: 카테고리 ID (None이면 환경변수 또는 기본값)
        status: 'publish' 또는 'draft' (None이면 환경변수 또는 publish)
        featured_image_url: 대표 이미지 URL (옵션)

    Returns:
        {"id": int, "url": str, "status": str}
    """
    wp_env = wp_env or {}
    url, user, app_password = get_wp_config(
        wp_env.get("wp_url_env", "WP_URL"),
        wp_env.get("wp_user_env", "WP_USER"),
        wp_env.get("wp_pass_env", "WP_APP_PASSWORD"),
    )
    auth = HTTPBasicAuth(user, app_password)

    # 기본값 처리
    if status is None:
        status = os.environ.get("WP_STATUS", "draft")
    if category_id is None:
        cat_env = os.environ.get("WP_CATEGORY_ID", "")
        category_id = int(cat_env) if cat_env.isdigit() else None

    # 태그 ID 변환
    tag_ids = get_or_create_tags(tags or [], wp_env=wp_env)

    # 대표 이미지 업로드 (URL → 미디어 라이브러리, 사이트별 credentials 사용)
    featured_media_id = None
    if featured_image_url:
        featured_media_id, _ = upload_image_from_url(
            featured_image_url, title, wp_env=wp_env,
            alt_text=focus_keyword or title,          # 포커스 키워드를 alt로
            caption_kr=f"{focus_keyword} 관련 이미지" if focus_keyword else title,
        )
        if featured_media_id:
            print(f"  🖼 대표 이미지 설정 완료 (ID: {featured_media_id})")

    # Rank Math 메타 필드 구성
    rank_math_meta = {}
    if focus_keyword:
        rank_math_meta["rank_math_focus_keyword"] = focus_keyword
    if seo_title:
        rank_math_meta["rank_math_title"] = seo_title
    if seo_description:
        rank_math_meta["rank_math_description"] = seo_description

    # 본문에 이미지 삽입 (대표 이미지와 별개인 본문 전용 이미지)
    final_content = content_html
    body_images = list(image_list) if image_list else []
    if body_images:
        final_content = _insert_images_into_content(
            content_html,
            body_images,
            alt=image_alt or title,
            focus_keyword=focus_keyword,   # 첫 번째 이미지에 포커스 키워드 alt 적용
        )

    # 포커스 키워드 → URL 슬러그 (Rank Math 'keyword in URL' 검사 통과)
    slug = focus_keyword.strip().replace(" ", "-") if focus_keyword else ""

    # 포스트 데이터 구성
    post_data = {
        "title": title,
        "content": final_content,
        "status": status,
    }
    if slug:
        post_data["slug"] = slug
    if excerpt:
        post_data["excerpt"] = excerpt
    if tag_ids:
        post_data["tags"] = tag_ids
    if category_id:
        post_data["categories"] = [category_id]
    if featured_media_id:
        post_data["featured_media"] = featured_media_id
    if rank_math_meta:
        post_data["meta"] = rank_math_meta

    # REST API 호출
    print(f"  WordPress에 포스트 전송 중... (status={status})")
    resp = requests.post(
        f"{url}/wp-json/wp/v2/posts",
        json=post_data,
        auth=auth,
        timeout=30,
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        post_id = data["id"]
        post_url = data["link"]
        print(f"  ✅ 발행 성공! ID: {post_id}")
        print(f"  🔗 URL: {post_url}")

        # Rank Math 메타 필드 별도 PATCH (더 안정적)
        if rank_math_meta:
            _update_rank_math_meta(url, auth, post_id, rank_math_meta)

        return {"id": post_id, "url": post_url, "status": status}
    else:
        print(f"  ❌ 발행 실패: {resp.status_code}")
        print(f"  응답: {resp.text[:500]}")
        resp.raise_for_status()


def _credit_to_korean(credit: str) -> str:
    """영문 크레딧 → 한글 캡션 변환 (소스·작가·라이선스 상세 표기)"""
    if not credit:
        return ""
    c = credit.strip()

    def _between(s: str, open_: str, close_: str) -> str:
        try:
            return s[s.rindex(open_) + 1: s.rindex(close_)]
        except ValueError:
            return ""

    if "NASA" in c:
        # "Image Credit: NASA (Title)" 형식
        title = _between(c, "(", ")")
        label = f" — {title}" if title else ""
        return (f'이미지 출처: <a href="https://images.nasa.gov" target="_blank" rel="noopener">'
                f'NASA</a>{label}')

    elif "Wikimedia Commons" in c:
        # "{artist} / Wikimedia Commons ({license})" 형식
        artist  = c.split(" / Wikimedia Commons")[0].strip()
        license_ = _between(c, "(", ")")
        artist_part = f" / {artist}" if artist else ""
        license_part = f" ({license_})" if license_ else ""
        return (f'이미지 출처: <a href="https://commons.wikimedia.org" target="_blank" rel="noopener">'
                f'Wikimedia Commons</a>{artist_part}{license_part}')

    elif "OpenVerse" in c:
        # "{creator} / OpenVerse ({license})" 형식
        creator  = c.split(" / OpenVerse")[0].strip()
        license_ = _between(c, "(", ")")
        creator_part = f" / {creator}" if creator and creator != "OpenVerse" else ""
        license_part = f" ({license_})" if license_ else ""
        return (f'이미지 출처: <a href="https://openverse.org" target="_blank" rel="noopener">'
                f'OpenVerse</a>{creator_part}{license_part}')

    elif "Pexels" in c:
        # "Photo by {photographer} on Pexels" 형식
        photographer = c.replace("Photo by ", "").replace(" on Pexels", "").strip()
        name_part = f" / {photographer}" if photographer else ""
        return (f'이미지 출처: <a href="https://www.pexels.com" target="_blank" rel="noopener">'
                f'Pexels</a>{name_part}')

    elif "Pixabay" in c:
        # "Image by {user} on Pixabay" 형식
        user = c.replace("Image by ", "").replace(" on Pixabay", "").strip()
        name_part = f" / {user}" if user else ""
        return (f'이미지 출처: <a href="https://pixabay.com" target="_blank" rel="noopener">'
                f'Pixabay</a>{name_part}')

    return f"이미지 출처: {c}"


def _make_img_block(image_url: str, alt: str = "", credit: str = None) -> str:
    """
    이미지 Gutenberg 블록 생성.
    wp:html 블록으로 감싸야 편집기에서 저장해도 이미지가 사라지지 않음.
    """
    caption_kr = _credit_to_korean(credit)
    figcaption = (
        f'<figcaption class="wp-element-caption" style="text-align:center;font-size:0.8em;color:#999;margin-top:4px;">'
        f'{caption_kr}</figcaption>'
        if caption_kr else ""
    )
    inner = (
        f'<figure class="wp-block-image size-large" style="text-align:center;margin:1.8em 0;">'
        f'<img src="{image_url}" alt="{alt}" style="max-width:100%;height:auto;border-radius:8px;" />'
        f'{figcaption}'
        f'</figure>'
    )
    # wp:html 블록으로 감싸기 → Gutenberg 편집 후 저장해도 보존됨
    return f'\n<!-- wp:html -->\n{inner}\n<!-- /wp:html -->\n'


def _insert_images_into_content(content_html: str, images: list[dict], alt: str = "",
                                focus_keyword: str = "") -> str:
    """
    Gutenberg 블록 형식 본문에 이미지 블록 삽입.
    H2 헤딩 블록(<!-- wp:heading {"level":2} -->) 뒤에 이미지를 순서대로 삽입.
    남은 이미지는 단락(paragraph) 블록 4개마다 삽입.
    """
    if not images:
        return content_html

    # 블록 단위로 분리 (Gutenberg 블록은 \n\n으로 구분)
    blocks = content_html.split('\n\n')
    result = []
    img_idx = 0

    for block in blocks:
        result.append(block)
        # H2 헤딩 블록 직후에 이미지 삽입 (블록 경계 바깥)
        if '<!-- wp:heading {"level":2} -->' in block and img_idx < len(images):
            img = images[img_idx]
            img_alt = focus_keyword if (img_idx == 0 and focus_keyword) else alt
            result.append(_make_img_block(img["url"], alt=img_alt, credit=img.get("credit")).strip())
            img_idx += 1

    # 남은 이미지는 paragraph 블록 4개마다 삽입
    if img_idx < len(images):
        final = []
        p_count = 0
        for block in result:
            final.append(block)
            if '<!-- wp:paragraph -->' in block:
                p_count += 1
                if p_count % 4 == 0 and img_idx < len(images):
                    img = images[img_idx]
                    img_alt = focus_keyword if (img_idx == 0 and focus_keyword) else alt
                    final.append(_make_img_block(img["url"], alt=img_alt, credit=img.get("credit")).strip())
                    img_idx += 1
        result = final

    return '\n\n'.join(result)


def _update_rank_math_meta(wp_url: str, auth, post_id: int, meta: dict):
    """
    Rank Math 전용 REST API(/rankmath/v1/updateMeta)로 SEO 메타 업데이트.
    WordPress 일반 meta API보다 안정적으로 저장됨.
    """
    try:
        # Rank Math 전용 API 호출
        rm_resp = requests.post(
            f"{wp_url}/wp-json/rankmath/v1/updateMeta",
            json={
                "objectID":   post_id,
                "objectType": "post",
                "meta": {
                    "focusKeyword": meta.get("rank_math_focus_keyword", ""),
                    "title":        meta.get("rank_math_title", ""),
                    "description":  meta.get("rank_math_description", ""),
                },
            },
            auth=auth,
            timeout=15,
        )
        if rm_resp.ok and rm_resp.json().get("slug"):
            kw    = meta.get("rank_math_focus_keyword", "")
            title = meta.get("rank_math_title", "")
            desc  = meta.get("rank_math_description", "")
            print(f"  🎯 Rank Math SEO 적용 완료!")
            print(f"     포커스 키워드: {kw}")
            print(f"     SEO 제목: {title}")
            print(f"     메타 설명: {desc[:50]}..." if desc else "     메타 설명: (없음)")
        else:
            # Rank Math API 실패 시 기존 WordPress meta API로 폴백
            patch_resp = requests.post(
                f"{wp_url}/wp-json/wp/v2/posts/{post_id}",
                json={"meta": meta},
                auth=auth,
                timeout=15,
            )
            if patch_resp.ok:
                print(f"  🎯 Rank Math SEO (폴백 방식) 적용")
            else:
                print(f"  ⚠ Rank Math 업데이트 실패: {rm_resp.status_code} / {rm_resp.text[:100]}")
    except Exception as e:
        print(f"  ⚠ Rank Math 메타 업데이트 오류: {e}")


def _optimize_image(raw_bytes: bytes, max_width: int = None, max_height: int = None,
                    quality: int = None, size_limit_kb: int = None) -> tuple[bytes, str]:
    """
    이미지 리사이즈 + 압축 최적화
    반환: (최적화된 바이트, content_type)
    """
    from PIL import Image
    import io

    # .env에서 설정값 읽기 (파라미터 없으면 환경변수 → 기본값 순)
    max_width     = max_width     or int(os.environ.get("IMAGE_MAX_WIDTH",     "1200"))
    max_height    = max_height    or int(os.environ.get("IMAGE_MAX_HEIGHT",    "900"))
    quality       = quality       or int(os.environ.get("IMAGE_QUALITY",       "82"))
    size_limit_kb = size_limit_kb or int(os.environ.get("IMAGE_SIZE_LIMIT_KB", "200"))

    img = Image.open(io.BytesIO(raw_bytes))

    # RGBA/P → RGB 변환 (JPEG는 알파채널 불가)
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 리사이즈 (비율 유지)
    w, h = img.size
    if w > max_width or h > max_height:
        img.thumbnail((max_width, max_height), Image.LANCZOS)
        w, h = img.size

    # 압축 (용량 초과 시 품질 자동 감소)
    for q in [quality, 72, 62, 50]:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q, optimize=True)
        size_kb = buf.tell() / 1024
        if size_kb <= size_limit_kb:
            break
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q, optimize=True)

    final_kb = buf.tell() / 1024
    print(f"  📐 이미지 최적화: {w}×{h}px / {final_kb:.0f}KB (품질 {q}%)")
    return buf.getvalue(), "image/jpeg"


def upload_image_from_url(image_url: str, title: str = "", wp_env: dict = None,
                          alt_text: str = "", caption_kr: str = "") -> tuple[int | None, str]:
    """
    외부 이미지 URL → 최적화 후 WordPress 미디어 라이브러리에 업로드
    반환: (미디어 ID, 미디어 URL)
    """
    wp_env = wp_env or {}
    wp_url, user, app_password = get_wp_config(
        wp_env.get("wp_url_env", "WP_URL"),
        wp_env.get("wp_user_env", "WP_USER"),
        wp_env.get("wp_pass_env", "WP_APP_PASSWORD"),
    )
    auth = HTTPBasicAuth(user, app_password)

    try:
        img_resp = requests.get(image_url, timeout=15)
        img_resp.raise_for_status()

        # 이미지 최적화 (리사이즈 + 압축)
        optimized_bytes, content_type = _optimize_image(img_resp.content)

        # 파일명은 ASCII만 사용
        import re as _re
        safe_title = _re.sub(r"[^\x00-\x7F]", "", title).strip().replace(" ", "-")[:30]
        filename = f"auto-{safe_title}.jpg" if safe_title else "auto-image.jpg"

        media_resp = requests.post(
            f"{wp_url}/wp-json/wp/v2/media",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": content_type,
            },
            data=optimized_bytes,
            auth=auth,
            timeout=30,
        )

        if media_resp.ok:
            media_data = media_resp.json()
            media_id = media_data["id"]
            media_url = media_data.get("source_url", "")
            print(f"  🖼 이미지 업로드 완료 (ID: {media_id})")

            # 업로드 후 한글 alt text + 캡션 설정
            meta_payload = {}
            if alt_text:
                meta_payload["alt_text"] = alt_text
            if caption_kr:
                meta_payload["caption"] = caption_kr
            if meta_payload:
                requests.post(
                    f"{wp_url}/wp-json/wp/v2/media/{media_id}",
                    json=meta_payload,
                    auth=auth,
                    timeout=15,
                )

            return media_id, media_url
        else:
            print(f"  ⚠ 이미지 업로드 실패: {media_resp.status_code}")

    except Exception as e:
        print(f"  ⚠ 이미지 처리 오류: {e}")

    return None, None


def test_connection(wp_env: dict = None) -> bool:
    """WordPress 연결 테스트"""
    try:
        wp_env = wp_env or {}
        url, user, app_password = get_wp_config(
            wp_env.get("wp_url_env", "WP_URL"),
            wp_env.get("wp_user_env", "WP_USER"),
            wp_env.get("wp_pass_env", "WP_APP_PASSWORD"),
        )
        auth = HTTPBasicAuth(user, app_password)
        resp = requests.get(
            f"{url}/wp-json/wp/v2/users/me",
            auth=auth,
            timeout=10,
        )
        if resp.ok:
            name = resp.json().get("name", "알 수 없음")
            print(f"  ✅ WordPress 연결 성공! (사용자: {name})")
            return True
        else:
            print(f"  ❌ 인증 실패: {resp.status_code} - {resp.text[:200]}")
            return False
    except ValueError as e:
        print(f"  ❌ 설정 오류: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        return False


def fetch_recent_posts(wp_env: dict, count: int = 8) -> list[dict]:
    """최근 발행(publish)된 포스트 목록 반환 — 내부 링크 삽입용"""
    try:
        url, user, app_password = get_wp_config(
            wp_env.get("wp_url_env", "WP_URL"),
            wp_env.get("wp_user_env", "WP_USER"),
            wp_env.get("wp_pass_env", "WP_APP_PASSWORD"),
        )
        auth = HTTPBasicAuth(user, app_password)
        resp = requests.get(
            f"{url}/wp-json/wp/v2/posts",
            params={"per_page": count, "status": "publish",
                    "_fields": "id,link,title", "orderby": "date", "order": "desc"},
            auth=auth,
            timeout=10,
        )
        if not resp.ok:
            return []
        return [
            {"title": p["title"]["rendered"], "url": p["link"]}
            for p in resp.json()
            if p.get("title", {}).get("rendered") and p.get("link")
        ]
    except Exception as e:
        print(f"  ⚠ 내부 링크용 포스트 조회 실패: {e}")
    return []


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=== WordPress 연결 테스트 ===")
    test_connection()
