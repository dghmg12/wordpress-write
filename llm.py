"""
llm.py - Gemini API 중앙 클라이언트 (Google Search Grounding 포함)

Google Search Grounding을 사용하면 모델이 실시간 웹 검색 결과를 참고해
최신 정보(상장 여부, 단종 제품, 최신 수치 등)를 반영할 수 있다.
"""
import os
import re
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"

# Search Grounding이 붙이는 인용 마커 패턴 제거용
_CITE_RE = re.compile(r"\s*\[cite:\s*[\d,\s]+\]", re.IGNORECASE)


def call_llm(prompt: str, max_tokens: int = 8096, use_search: bool = True) -> str:
    """
    Gemini API 호출. use_search=True면 Google Search Grounding 활성화.
    반환: 생성된 텍스트 문자열 (인용 마커 제거됨)
    """
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    tools = [types.Tool(google_search=types.GoogleSearch())] if use_search else []

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=tools,
            max_output_tokens=max_tokens,
        ),
    )
    text = response.text or ""
    return _CITE_RE.sub("", text)
