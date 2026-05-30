# wp-auto-poster 🤖

웹 크롤링 → Claude AI 글 작성 → WordPress 자동 발행 봇

## 흐름

```
RSS 피드 크롤링 → Claude API로 재작성 → WordPress REST API 발행
```

## 설치

```bash
cd C:\wp-auto-poster
pip install -r requirements.txt
```

## 설정

`.env` 파일에 아래 값을 채워 넣는다.

| 항목 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `WP_URL` | 워드프레스 사이트 주소 (예: https://blacknudge.com) |
| `WP_USER` | 워드프레스 관리자 아이디 |
| `WP_APP_PASSWORD` | Application Password (설정 → 사용자 → 프로필에서 생성) |
| `WP_STATUS` | `publish`(즉시발행) 또는 `draft`(임시저장) |
| `RSS_FEEDS` | 크롤링할 RSS URL (쉼표 구분, 비워두면 기본 뉴스 사용) |
| `CRAWL_KEYWORDS` | 필터 키워드 (쉼표 구분, 비워두면 전체 수집) |

### WordPress Application Password 발급 방법
1. 워드프레스 관리자 → 사용자 → 프로필
2. 스크롤 내려서 "애플리케이션 비밀번호" 섹션
3. 이름 입력 후 "새 애플리케이션 비밀번호 추가" 클릭
4. 생성된 비밀번호를 `.env`의 `WP_APP_PASSWORD`에 복사

## 실행 방법

```bash
# WordPress 연결 테스트
python main.py --test-wp

# 크롤링 테스트
python main.py --test-crawl

# 글만 생성 (발행 안 함)
python main.py --dry-run

# 특정 주제로 실행
python main.py --topic 부동산

# 전체 자동 실행
python main.py
```

## 자동화 (Windows 작업 스케줄러)

매일 오전 9시 자동 실행:

1. 작업 스케줄러 열기 (Win+R → `taskschd.msc`)
2. 기본 작업 만들기
3. 트리거: 매일 09:00
4. 동작: 프로그램 시작 → `python` / 인수: `C:\wp-auto-poster\main.py`
