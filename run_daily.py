"""
run_daily.py - 매일 자동 실행 스크립트
  - 실행 조건: 월~토 (일요일 자동 스킵)
  - blacknudge: 라이프스타일 (월·화·수·금) / 잡학 (목, 1회/주)
  - newbicon:   우주 경제 분석 (월~금) / 우주과학 (토)

실행: py run_daily.py
스케줄: 월~토 오전 8시 (GitHub Actions / Windows 작업 스케줄러)
"""
import sys
import os
import random
import logging
from datetime import datetime, timezone, timedelta

# 로그 설정
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

KST = timezone(timedelta(hours=9))
today_str = datetime.now(KST).strftime('%Y%m%d')
log_file = os.path.join(LOG_DIR, f'daily_{today_str}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()


def run_site(site_key: str, topic: str):
    """단일 사이트·주제 파이프라인 실행"""
    from main import run_full_pipeline
    from sites import get_site
    cfg = get_site(site_key)
    cfg['_key'] = site_key
    run_full_pipeline(cfg, topic=topic)


def main():
    now = datetime.now(KST)

    # ── 일요일만 스킵 (0=월 ... 5=토 ... 6=일)
    weekday = now.weekday()
    if weekday == 6:
        logging.info('오늘은 일요일 → 자동 포스팅 없음 (월~토만 실행)')
        return

    day_names = ['월', '화', '수', '목', '금', '토']
    logging.info('=' * 52)
    logging.info(f'  일일 자동 포스팅 시작: {now.strftime("%Y-%m-%d")} ({day_names[weekday]}) KST')
    logging.info('=' * 52)

    results = []

    # ── blacknudge: 목요일만 잡학, 나머지 평일(월~수·금)은 라이프스타일 ──
    if weekday < 5:  # 월~금 (토요일 블랙넛지 없음)
        if weekday == 3:  # 목요일: 잡학 (1회/주)
            logging.info('\n[잡학] 블랙넛지 잡학 포스팅...')
            try:
                from trivia import post_trivia
                post_trivia()
                results.append('블랙넛지/잡학 ✅')
            except Exception as e:
                logging.error(f'  ❌ 블랙넛지/잡학 오류: {e}')
                results.append('블랙넛지/잡학 ❌')
        else:  # 월·화·수·금: 라이프스타일
            logging.info('\n[라이프스타일] 블랙넛지 라이프스타일 포스팅...')
            try:
                from lifestyle import post_lifestyle
                post_lifestyle()
                results.append('블랙넛지/라이프스타일 ✅')
            except Exception as e:
                logging.error(f'  ❌ 블랙넛지/라이프스타일 오류: {e}')
                results.append('블랙넛지/라이프스타일 ❌')

    # ── newbicon: 우주 경제 분석 (월~금) / 우주과학 (토) ────
    logging.info('\n[뉴비콘] 포스팅...')
    try:
        from space import post_space
        post_space()
        results.append('뉴비콘 ✅')
    except Exception as e:
        logging.error(f'  ❌ 뉴비콘 오류: {e}')
        results.append('뉴비콘 ❌')

    # ── 최종 요약 ───────────────────────────────────────────
    end = datetime.now(KST)
    logging.info('\n' + '=' * 52)
    logging.info(f'  완료: {end.strftime("%H:%M")} KST')
    for r in results:
        logging.info(f'    {r}')
    logging.info('=' * 52)


if __name__ == '__main__':
    main()
