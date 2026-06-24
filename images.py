"""
images.py - 무료 이미지 검색 및 다운로드 모듈

지원 소스 (우선순위 순):
  0. NASA Image Library   - API 키 불필요, 우주 관련 글 우선 사용
  1. Wikimedia Commons    - API 키 불필요, CC/공개 도메인, 우주·과학 이미지 풍부
  2. OpenVerse            - API 키 불필요 (100 req/day), CC 상업 가능 이미지
  3. Pexels API           - PEXELS_API_KEY 필요 (무료 등록)
  4. Pixabay API          - PIXABAY_API_KEY 필요 (무료 등록)
  5. 모두 없으면 이미지 건너뜀

API 키 발급 (선택):
  Pexels  → https://www.pexels.com/api/
  Pixabay → https://pixabay.com/api/docs/
"""
import requests
import os
import random
from bs4 import BeautifulSoup


def fetch_image(query: str) -> dict | None:
    """
    글 주제에 맞는 무료 이미지 1개 검색
    반환: {"url": str, "alt": str, "credit": str} 또는 None
    """
    results = fetch_multiple_images(query, count=1)
    return results[0] if results else None


def fetch_featured_image(query: str, nasa: bool = False) -> dict | None:
    """
    대표 이미지 전용 검색 - 랜덤화 없이 가장 관련성 높은 이미지 1개 반환.
    nasa=True 이면 NASA → Wikimedia → OpenVerse → Pexels → Pixabay 순서로 시도.
    nasa=False 이면 OpenVerse → Wikimedia → Pexels → Pixabay 순서로 시도.
    """
    pexels_key  = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()

    if nasa:
        sources = [
            lambda: _fetch_nasa_featured(query),
            lambda: _fetch_wikimedia_featured(query),
            lambda: _fetch_openverse_featured(query),
            lambda: (_fetch_pexels_featured(query, pexels_key) if pexels_key else None),
            lambda: (_fetch_pixabay_featured(query, pixabay_key) if pixabay_key else None),
        ]
    else:
        sources = [
            lambda: _fetch_openverse_featured(query),
            lambda: _fetch_wikimedia_featured(query),
            lambda: (_fetch_pexels_featured(query, pexels_key) if pexels_key else None),
            lambda: (_fetch_pixabay_featured(query, pixabay_key) if pixabay_key else None),
        ]

    for source_fn in sources:
        result = source_fn()
        if result:
            return result

    print("  ⚠ 대표 이미지를 찾지 못했습니다.")
    return None


def _nasa_preview_to_large(url: str) -> str:
    """NASA 썸네일 URL → 대형 이미지 URL로 변환"""
    if url.endswith('~thumb.jpg'):
        return url[:-len('~thumb.jpg')] + '~large.jpg'
    return url


def _fetch_nasa_featured(query: str) -> dict | None:
    """NASA Image Library — API 키 불필요, 가장 관련성 높은 이미지 1개"""
    try:
        resp = requests.get(
            "https://images-api.nasa.gov/search",
            params={"q": query, "media_type": "image"},
            timeout=10,
        )
        items = resp.json().get("collection", {}).get("items", []) if resp.ok else []
        for item in items:
            links = item.get("links", [])
            data  = item.get("data", [{}])[0]
            for link in links:
                if link.get("rel") == "preview" and link.get("href", "").endswith(".jpg"):
                    url = _nasa_preview_to_large(link["href"])
                    title = data.get("title", query)
                    return {
                        "url":    url,
                        "alt":    title,
                        "credit": f"Image Credit: NASA ({title})",
                        "source": "nasa",
                    }
    except Exception as e:
        print(f"  ⚠ NASA 이미지 오류: {e}")
    return None


def _fetch_nasa_multiple(query: str, count: int) -> list[dict]:
    """NASA Image Library — 여러 장 검색 (랜덤 셔플)"""
    try:
        resp = requests.get(
            "https://images-api.nasa.gov/search",
            params={"q": query, "media_type": "image"},
            timeout=10,
        )
        items = resp.json().get("collection", {}).get("items", []) if resp.ok else []
        results = []
        random.shuffle(items)
        for item in items:
            links = item.get("links", [])
            data  = item.get("data", [{}])[0]
            for link in links:
                if link.get("rel") == "preview" and link.get("href", "").endswith(".jpg"):
                    url = _nasa_preview_to_large(link["href"])
                    title = data.get("title", query)
                    results.append({
                        "url":    url,
                        "alt":    title,
                        "credit": f"Image Credit: NASA ({title})",
                        "source": "nasa",
                    })
                    break
            if len(results) >= count:
                break
        return results
    except Exception as e:
        print(f"  ⚠ NASA 다중 이미지 오류: {e}")
    return []


def _fetch_wikimedia_featured(query: str) -> dict | None:
    """Wikimedia Commons — API 키 불필요, CC/공개 도메인 이미지 1개"""
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrnamespace": 6,
                "gsrlimit": 10,
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata",
                "iiurlwidth": 1200,
                "format": "json",
            },
            timeout=10,
        )
        if not resp.ok:
            return None
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            if not info.get("mime", "").startswith("image/"):
                continue
            url = info.get("thumburl") or info.get("url")
            if not url:
                continue
            meta     = info.get("extmetadata", {})
            artist   = BeautifulSoup(
                meta.get("Artist", {}).get("value", "Wikimedia Commons"), "html.parser"
            ).get_text()[:60]
            license_short = meta.get("LicenseShortName", {}).get("value", "CC")
            title = page.get("title", query).replace("File:", "")
            return {
                "url":    url,
                "alt":    title,
                "credit": f"{artist} / Wikimedia Commons ({license_short})",
                "source": "wikimedia",
            }
    except Exception as e:
        print(f"  ⚠ Wikimedia 이미지 오류: {e}")
    return None


def _fetch_wikimedia_multiple(query: str, count: int) -> list[dict]:
    """Wikimedia Commons — API 키 불필요, 여러 장 (랜덤 셔플)"""
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrnamespace": 6,
                "gsrlimit": min(count * 3, 20),
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata",
                "iiurlwidth": 1200,
                "format": "json",
            },
            timeout=10,
        )
        if not resp.ok:
            return []
        pages = list(resp.json().get("query", {}).get("pages", {}).values())
        random.shuffle(pages)
        results = []
        for page in pages:
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            if not info.get("mime", "").startswith("image/"):
                continue
            url = info.get("thumburl") or info.get("url")
            if not url:
                continue
            meta     = info.get("extmetadata", {})
            artist   = BeautifulSoup(
                meta.get("Artist", {}).get("value", "Wikimedia Commons"), "html.parser"
            ).get_text()[:60]
            license_short = meta.get("LicenseShortName", {}).get("value", "CC")
            title = page.get("title", query).replace("File:", "")
            results.append({
                "url":    url,
                "alt":    title,
                "credit": f"{artist} / Wikimedia Commons ({license_short})",
                "source": "wikimedia",
            })
            if len(results) >= count:
                break
        return results
    except Exception as e:
        print(f"  ⚠ Wikimedia 다중 이미지 오류: {e}")
    return []


def _fetch_openverse_featured(query: str) -> dict | None:
    """OpenVerse (WordPress 재단) — API 키 불필요, CC 상업 가능 이미지 1개"""
    try:
        resp = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": query,
                "page_size": 5,
                "license_type": "commercial",
                "mature": "false",
            },
            headers={"User-Agent": "NewbiconSpaceBot/1.0 (blog automation, educational)"},
            timeout=10,
        )
        if not resp.ok:
            return None
        results = resp.json().get("results", [])
        if results:
            r = results[0]
            url = r.get("url", "")
            if not url:
                return None
            return {
                "url":    url,
                "alt":    r.get("title", query),
                "credit": f"{r.get('creator', 'OpenVerse')} / OpenVerse ({r.get('license', 'CC').upper()})",
                "source": "openverse",
            }
    except Exception as e:
        print(f"  ⚠ OpenVerse 이미지 오류: {e}")
    return None


def _fetch_openverse_multiple(query: str, count: int) -> list[dict]:
    """OpenVerse — API 키 불필요, 여러 장 (랜덤 셔플)"""
    try:
        resp = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": query,
                "page_size": min(count * 3, 20),
                "license_type": "commercial",
                "mature": "false",
            },
            headers={"User-Agent": "NewbiconSpaceBot/1.0 (blog automation, educational)"},
            timeout=10,
        )
        if not resp.ok:
            return []
        results = resp.json().get("results", [])
        random.shuffle(results)
        return [
            {
                "url":    r["url"],
                "alt":    r.get("title", query),
                "credit": f"{r.get('creator', 'OpenVerse')} / OpenVerse ({r.get('license', 'CC').upper()})",
                "source": "openverse",
            }
            for r in results[:count]
            if r.get("url")
        ]
    except Exception as e:
        print(f"  ⚠ OpenVerse 다중 이미지 오류: {e}")
    return []


def _fetch_pexels_featured(query: str, api_key: str) -> dict | None:
    """Pexels - page 1, 첫 번째 결과 반환 (랜덤화 없음)"""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            timeout=10,
        )
        photos = resp.json().get("photos", []) if resp.ok else []
        if photos:
            p = photos[0]
            return {
                "url": p["src"]["large2x"],
                "alt": p.get("alt") or query,
                "credit": f"Photo by {p['photographer']} on Pexels",
                "source": "pexels",
            }
    except Exception as e:
        print(f"  ⚠ Pexels 대표 이미지 오류: {e}")
    return None


def _fetch_pixabay_featured(query: str, api_key: str) -> dict | None:
    """Pixabay - page 1, 첫 번째 결과 반환 (랜덤화 없음)"""
    try:
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "per_page": 5,
                "safesearch": "true",
            },
            timeout=10,
        )
        hits = resp.json().get("hits", []) if resp.ok else []
        if hits:
            h = hits[0]
            return {
                "url": h["largeImageURL"],
                "alt": query,
                "credit": f"Image by {h['user']} on Pixabay",
                "source": "pixabay",
            }
    except Exception as e:
        print(f"  ⚠ Pixabay 대표 이미지 오류: {e}")
    return None


def _fetch_openverse_illustrations_multiple(query: str, count: int) -> list[dict]:
    """OpenVerse — 일러스트 카테고리 한정"""
    try:
        resp = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": query,
                "page_size": min(count * 3, 20),
                "license_type": "commercial",
                "category": "illustration",
                "mature": "false",
            },
            headers={"User-Agent": "NewbiconSpaceBot/1.0 (blog automation, educational)"},
            timeout=10,
        )
        if not resp.ok:
            return []
        results = resp.json().get("results", [])
        random.shuffle(results)
        return [
            {
                "url":    r["url"],
                "alt":    r.get("title", query),
                "credit": f"{r.get('creator', 'OpenVerse')} / OpenVerse ({r.get('license', 'CC').upper()})",
                "source": "openverse",
            }
            for r in results[:count]
            if r.get("url")
        ]
    except Exception as e:
        print(f"  ⚠ OpenVerse 일러스트 오류: {e}")
    return []


def _fetch_pixabay_illustrations_multiple(query: str, api_key: str, count: int) -> list[dict]:
    """Pixabay — image_type=illustration 한정"""
    try:
        fetch_count = min(max(count * 4, 15), 50)
        page = random.randint(1, 3)
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key,
                "q": query,
                "image_type": "illustration",
                "orientation": "horizontal",
                "per_page": fetch_count,
                "page": page,
                "safesearch": "true",
            },
            timeout=10,
        )
        hits = resp.json().get("hits", []) if resp.ok else []
        if not hits:
            resp2 = requests.get(
                "https://pixabay.com/api/",
                params={
                    "key": api_key,
                    "q": query,
                    "image_type": "illustration",
                    "orientation": "horizontal",
                    "per_page": fetch_count,
                    "safesearch": "true",
                },
                timeout=10,
            )
            hits = resp2.json().get("hits", []) if resp2.ok else []
        random.shuffle(hits)
        return [
            {
                "url":    h["largeImageURL"],
                "alt":    query,
                "credit": f"Image by {h['user']} on Pixabay",
                "source": "pixabay",
            }
            for h in hits[:count]
        ]
    except Exception as e:
        print(f"  ⚠ Pixabay 일러스트 오류: {e}")
    return []


def fetch_multiple_images(query: str, count: int = 4, nasa: bool = False) -> list[dict]:
    """
    글 주제에 맞는 무료 이미지 여러 장 검색 (사진 + 일러스트 혼합)
    - 사진 슬롯: ceil(count/2) — 실사 사진
    - 일러스트 슬롯: floor(count/2) — 디지털 아트·일러스트
    - 모자라면 상대방 유형으로 보충
    반환: [{"url": str, "alt": str, "credit": str}, ...]
    """
    pexels_key  = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()

    photo_target  = (count + 1) // 2   # ceil
    illust_target = count // 2          # floor

    # ── 사진 수집 ─────────────────────────────────────────────
    photos: list[dict] = []

    def _fill_photos(fetch_fn, *args):
        if len(photos) >= photo_target:
            return
        needed = photo_target - len(photos)
        photos.extend(fetch_fn(*args, needed))

    if nasa:
        _fill_photos(_fetch_nasa_multiple, query)
    _fill_photos(_fetch_openverse_multiple, query)
    _fill_photos(_fetch_wikimedia_multiple, query)
    if pexels_key:
        _fill_photos(_fetch_pexels_multiple, query, pexels_key)
    if pixabay_key:
        _fill_photos(_fetch_pixabay_multiple, query, pixabay_key)

    # ── 일러스트 수집 ─────────────────────────────────────────
    illusts: list[dict] = []

    def _fill_illusts(fetch_fn, *args):
        if len(illusts) >= illust_target:
            return
        needed = illust_target - len(illusts)
        illusts.extend(fetch_fn(*args, needed))

    if illust_target > 0:
        _fill_illusts(_fetch_openverse_illustrations_multiple, query)
        if pixabay_key:
            _fill_illusts(_fetch_pixabay_illustrations_multiple, query, pixabay_key)

    # ── 부족분 보충 (사진으로 일러스트 슬롯 대체, 반대도 가능) ─
    combined = photos + illusts
    if len(combined) < count:
        all_photos = photos + illusts  # 이미 있는 것 제외
        # 사진으로 추가 채움
        if pexels_key:
            extra = _fetch_pexels_multiple(query, pexels_key, count - len(combined))
            combined.extend(extra)
        if len(combined) < count and pixabay_key:
            extra = _fetch_pixabay_multiple(query, pixabay_key, count - len(combined))
            combined.extend(extra)

    random.shuffle(combined)

    if not combined:
        print("  ⚠ 이미지를 하나도 찾지 못했습니다.")
    return combined[:count]


def _fetch_pexels_multiple(query: str, api_key: str, count: int) -> list[dict]:
    """Pexels API로 이미지 여러 장 검색 (랜덤 페이지로 다양성 확보)"""
    try:
        fetch_count = max(count * 4, 15)   # 넉넉히 가져온 뒤 랜덤 선택
        page = random.randint(1, 4)
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": fetch_count,
                    "orientation": "landscape", "page": page},
            timeout=10,
        )
        photos = resp.json().get("photos", []) if resp.ok else []
        # 결과 없으면 page=1로 재시도
        if not photos:
            resp2 = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": api_key},
                params={"query": query, "per_page": fetch_count, "orientation": "landscape"},
                timeout=10,
            )
            photos = resp2.json().get("photos", []) if resp2.ok else []

        random.shuffle(photos)
        return [
            {
                "url": p["src"]["large2x"],
                "alt": p.get("alt") or query,
                "credit": f"Photo by {p['photographer']} on Pexels",
                "source": "pexels",
            }
            for p in photos[:count]
        ]
    except Exception as e:
        print(f"  ⚠ Pexels 오류: {e}")
    return []


def _fetch_pixabay_multiple(query: str, api_key: str, count: int) -> list[dict]:
    """Pixabay API로 이미지 여러 장 검색 (랜덤 페이지로 다양성 확보)"""
    try:
        fetch_count = min(max(count * 4, 15), 50)   # 넉넉히 가져온 뒤 랜덤 선택
        page = random.randint(1, 5)
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "per_page": fetch_count,
                "page": page,
                "safesearch": "true",
            },
            timeout=10,
        )
        hits = resp.json().get("hits", []) if resp.ok else []
        # 결과 없으면 page=1로 재시도
        if not hits:
            resp2 = requests.get(
                "https://pixabay.com/api/",
                params={
                    "key": api_key,
                    "q": query,
                    "image_type": "photo",
                    "orientation": "horizontal",
                    "per_page": fetch_count,
                    "safesearch": "true",
                },
                timeout=10,
            )
            hits = resp2.json().get("hits", []) if resp2.ok else []

        random.shuffle(hits)
        return [
            {
                "url": h["largeImageURL"],
                "alt": query,
                "credit": f"Image by {h['user']} on Pixabay",
                "source": "pixabay",
            }
            for h in hits[:count]
        ]
    except Exception as e:
        print(f"  ⚠ Pixabay 오류: {e}")
    return []


def _fetch_pexels(query: str, api_key: str) -> dict | None:
    """Pexels API로 이미지 검색"""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={
                "query": query,
                "per_page": 5,
                "orientation": "landscape",
                "locale": "ko-KR",
            },
            timeout=10,
        )
        if not resp.ok:
            return None

        photos = resp.json().get("photos", [])
        if not photos:
            # 영어로 재시도
            resp2 = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": api_key},
                params={"query": query, "per_page": 5, "orientation": "landscape"},
                timeout=10,
            )
            photos = resp2.json().get("photos", []) if resp2.ok else []

        if photos:
            photo = photos[0]
            return {
                "url": photo["src"]["large2x"],
                "alt": photo.get("alt") or query,
                "credit": f"Photo by {photo['photographer']} on Pexels",
                "source": "pexels",
            }
    except Exception as e:
        print(f"  ⚠ Pexels 오류: {e}")
    return None


def _fetch_pixabay(query: str, api_key: str) -> dict | None:
    """Pixabay API로 이미지 검색"""
    try:
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "per_page": 5,
                "lang": "ko",
                "safesearch": "true",
            },
            timeout=10,
        )
        if not resp.ok:
            return None

        hits = resp.json().get("hits", [])
        if not hits:
            # 영어로 재시도
            resp2 = requests.get(
                "https://pixabay.com/api/",
                params={
                    "key": api_key,
                    "q": query,
                    "image_type": "photo",
                    "orientation": "horizontal",
                    "per_page": 5,
                    "safesearch": "true",
                },
                timeout=10,
            )
            hits = resp2.json().get("hits", []) if resp2.ok else []

        if hits:
            hit = hits[0]
            return {
                "url": hit["largeImageURL"],
                "alt": query,
                "credit": f"Image by {hit['user']} on Pixabay",
                "source": "pixabay",
            }
    except Exception as e:
        print(f"  ⚠ Pixabay 오류: {e}")
    return None


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    test_query = "rocket launch space"
    print(f"=== 이미지 검색 테스트: '{test_query}' ===")
    result = fetch_image(test_query)
    if result:
        print(f"URL   : {result['url']}")
        print(f"Alt   : {result['alt']}")
        print(f"Credit: {result['credit']}")
    else:
        print("이미지 없음")
