"""
run_daily.py - 매일 자동 실행 스크립트
  - 실행 조건: 월~금요일만 (주말 자동 스킵)
  - blacknudge: 생활속 잡학 1개 (임시글)
  - newbicon:   우주과학 1개 (임시글)

실행: py run_daily.py
스케줄: 월~금 오전 8시 (GitHub Actions / Windows 작업 스케줄러)
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

    # ── 주말 체크 (0=월 ... 6=일)
    weekday = now.weekday()
    if weekday >= 5:
        day_names = {5: '토요일', 6: '일요일'}
        logging.info(f'오늘은 {day_names[weekday]} → 자동 포스팅 없음 (월~금만 실행)')
        return

    day_names = ['월', '화', '수', '목', '금']
    logging.info('=' * 52)
    logging.info(f'  일일 자동 포스팅 시작: {now.strftime("%Y-%m-%d")} ({day_names[weekday]}) KST')
    logging.info('=' * 52)

    results = []

    # ── blacknudge: 생활속 잡학 1개 ───────────────────────
    logging.info('\n[잡학] 블랙넛지 잡학 포스팅...')
    try:
        from trivia import post_trivia
        post_trivia()
        results.append('블랙넛지/잡학 ✅')
    except Exception as e:
        logging.error(f'  ❌ 블랙넛지/잡학 오류: {e}')
        results.append('블랙넛지/잡학 ❌')

    # ── newbicon: 우주과학 1개 (매일 고정) ────────────────
    logging.info('\n[우주과학] 뉴비콘 우주과학 포스팅...')
    try:
        from space import post_space
        post_space()
        results.append('뉴비콘/우주과학 ✅')
    except Exception as e:
        logging.error(f'  ❌ 뉴비콘/우주과학 오류: {e}')
        results.append('뉴비콘/우주과학 ❌')

    # ── 최종 요약 ───────────────────────────────────────────
    end = datetime.now(KST)
    logging.info('\n' + '=' * 52)
    logging.info(f'  완료: {end.strftime("%H:%M")} KST')
    for r in results:
        logging.info(f'    {r}')
    logging.info('=' * 52)


if __name__ == '__main__':
    main()
