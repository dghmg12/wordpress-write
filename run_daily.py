"""
run_daily.py - 매일 자동 실행 스크립트
  - blacknudge: 건강/운동/식단 중 2개 랜덤
  - newbicon:   경제/부동산/투자 중 2개 랜덤
  - newbicon:   한 입 지식 1개 (매일 고정)

실행: py run_daily.py
스케줄: 매일 오전 8시 (Windows 작업 스케줄러)
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
    logging.info('=' * 52)
    logging.info(f'  일일 자동 포스팅 시작: {now.strftime("%Y-%m-%d %H:%M")} KST')
    logging.info('=' * 52)

    results = []

    # ── blacknudge: 건강/운동/식단 중 2개 ──────────────────
    health_pool = ['건강', '운동', '식단']
    health_picks = random.sample(health_pool, 2)
    logging.info(f'\n[blacknudge] 오늘 주제: {health_picks}')

    for topic in health_picks:
        try:
            run_site('health', topic)
            results.append(f'blacknudge/{topic} ✅')
        except Exception as e:
            logging.error(f'  ❌ blacknudge/{topic} 오류: {e}')
            results.append(f'blacknudge/{topic} ❌')

    # ── newbicon: 경제/부동산/투자 중 2개 ──────────────────
    economy_pool = ['경제', '부동산', '투자']
    economy_picks = random.sample(economy_pool, 2)
    logging.info(f'\n[newbicon] 오늘 주제: {economy_picks}')

    for topic in economy_picks:
        try:
            run_site('economy', topic)
            results.append(f'newbicon/{topic} ✅')
        except Exception as e:
            logging.error(f'  ❌ newbicon/{topic} 오류: {e}')
            results.append(f'newbicon/{topic} ❌')

    # ── 한 입 지식 (매일 고정) ──────────────────────────────
    logging.info('\n[한 입 지식] 경제 용어 포스팅...')
    try:
        from bite_knowledge import post_bite_knowledge
        post_bite_knowledge()
        results.append('한 입 지식 ✅')
    except Exception as e:
        logging.error(f'  ❌ 한 입 지식 오류: {e}')
        results.append('한 입 지식 ❌')

    # ── 최종 요약 ───────────────────────────────────────────
    end = datetime.now(KST)
    logging.info('\n' + '=' * 52)
    logging.info(f'  완료: {end.strftime("%H:%M")} KST')
    for r in results:
        logging.info(f'    {r}')
    logging.info('=' * 52)


if __name__ == '__main__':
    main()
