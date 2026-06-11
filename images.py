"""
images.py - 무료 이미지 검색 및 다운로드 모듈

지원 소스:
  0. NASA Image Library (API 키 불필요, 우주 관련 글 우선 사용)
  1. Pexels API (PEXELS_API_KEY 필요, 무료 등록)
  2. Pixabay API (PIXABAY_API_KEY 필요, 무료 등록)
  3. 모두 없으면 이미지 건너뜀

API 키 발급:
  Pexels  → https://www.pexels.com/api/
  Pixabay → https://pixabay.com/api/docs/
"""
import requests
import os
import random


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
    nasa=True 이면 NASA 이미지 라이브러리를 가장 먼저 시도한다.
    """
    if nasa:
        result = _fetch_nasa_featured(query)
        if result:
            return result

    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()

    if pexels_key:
        result = _fetch_pexels_featured(query, pexels_key)
        if result:
            return result

    if pixabay_key:
        result = _fetch_pixabay_featured(query, pixabay_key)
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


def fetch_multiple_images(query: str, count: int = 4, nasa: bool = False) -> list[dict]:
    """
    글 주제에 맞는 무료 이미지 여러 장 검색 (중복 없이)
    nasa=True 이면 NASA 이미지를 먼저 가져오고 부족하면 Pexels/Pixabay로 보충.
    반환: [{"url": str, "alt": str, "credit": str}, ...]
    """
    results = []

    if nasa:
        nasa_imgs = _fetch_nasa_multiple(query, count)
        results.extend(nasa_imgs)
        if len(results) >= count:
            return results[:count]

    remaining = count - len(results)
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()

    if pexels_key and remaining > 0:
        pexels_imgs = _fetch_pexels_multiple(query, pexels_key, remaining)
        results.extend(pexels_imgs)

    if pixabay_key and len(results) < count:
        remaining = count - len(results)
        pixabay_imgs = _fetch_pixabay_multiple(query, pixabay_key, remaining)
        results.extend(pixabay_imgs)

    if not results:
        print("  ⚠ 이미지 API 키 없음 (PEXELS_API_KEY 또는 PIXABAY_API_KEY를 .env에 설정하세요)")
    return results[:count]


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

    test_query = "건강한 생활"
    print(f"=== 이미지 검색 테스트: '{test_query}' ===")
    result = fetch_image(test_query)
    if result:
        print(f"URL   : {result['url']}")
        print(f"Alt   : {result['alt']}")
        print(f"Credit: {result['credit']}")
    else:
        print("이미지 없음")
