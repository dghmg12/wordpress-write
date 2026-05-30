"""
images.py - 무료 이미지 검색 및 다운로드 모듈

지원 소스:
  1. Pexels API (PEXELS_API_KEY 필요, 무료 등록)
  2. Pixabay API (PIXABAY_API_KEY 필요, 무료 등록)
  3. 둘 다 없으면 이미지 건너뜀

API 키 발급:
  Pexels  → https://www.pexels.com/api/
  Pixabay → https://pixabay.com/api/docs/
"""
import requests
import os


def fetch_image(query: str) -> dict | None:
    """
    글 주제에 맞는 무료 이미지 1개 검색
    반환: {"url": str, "alt": str, "credit": str} 또는 None
    """
    results = fetch_multiple_images(query, count=1)
    return results[0] if results else None


def fetch_multiple_images(query: str, count: int = 4) -> list[dict]:
    """
    글 주제에 맞는 무료 이미지 여러 장 검색 (중복 없이)
    반환: [{"url": str, "alt": str, "credit": str}, ...]
    """
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()

    if pexels_key:
        results = _fetch_pexels_multiple(query, pexels_key, count)
        if results:
            return results

    if pixabay_key:
        results = _fetch_pixabay_multiple(query, pixabay_key, count)
        if results:
            return results

    print("  ⚠ 이미지 API 키 없음 (PEXELS_API_KEY 또는 PIXABAY_API_KEY를 .env에 설정하세요)")
    return []


def _fetch_pexels_multiple(query: str, api_key: str, count: int) -> list[dict]:
    """Pexels API로 이미지 여러 장 검색"""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": max(count, 5), "orientation": "landscape"},
            timeout=10,
        )
        photos = resp.json().get("photos", []) if resp.ok else []
        if not photos:
            # 영어로 재시도
            resp2 = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": api_key},
                params={"query": query, "per_page": max(count, 5), "orientation": "landscape"},
                timeout=10,
            )
            photos = resp2.json().get("photos", []) if resp2.ok else []

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
    """Pixabay API로 이미지 여러 장 검색"""
    try:
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "per_page": max(count, 5),
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
                    "image_type": "photo",
                    "orientation": "horizontal",
                    "per_page": max(count, 5),
                    "safesearch": "true",
                    "lang": "en",
                },
                timeout=10,
            )
            hits = resp2.json().get("hits", []) if resp2.ok else []

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
