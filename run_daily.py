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

    # ── blacknudge: 월~금 라이프스타일 (음식/문화·여행/외출·건강/운동 랜덤) ──
    if weekday < 5:  # 월~금 (토요일 블랙넛지 없음)
        # next_post.json 오버라이드 확인 (하루 한정 주제 지정)
        import json as _json, os as _os
        _override_file = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'next_post.json')
        _theme_override = None
        if _os.path.exists(_override_file):
            try:
                with open(_override_file, encoding='utf-8') as _f:
                    _data = _json.load(_f)
                if _data.get('date') == now.strftime('%Y-%m-%d') and _data.get('site') == 'blacknudge_lifestyle':
                    _theme_override = _data.get('theme')
                    _os.remove(_override_file)
                    logging.info(f'  📌 주제 오버라이드 적용: {_theme_override["name"]}')
            except Exception as _e:
                logging.warning(f'  ⚠ next_post.json 읽기 실패: {_e}')

        logging.info('\n[라이프스타일] 블랙넛지 라이프스타일 포스팅...')
        try:
            from lifestyle import post_lifestyle
            post_lifestyle(theme_override=_theme_override)
            results.append('블랙넛지/라이프스타일 ✅')
        except Exception as e:
            logging.error(f'  ❌ 블랙넛지/라이프스타일 오류: {e}')
            results.append('블랙넛지/라이프스타일 ❌')

    # ── newbicon: 발행 중지 ────────────────────────────────
    logging.info('\n[뉴비콘] 발행 중지 중 → 건너뜀')

    # ── 최종 요약 ───────────────────────────────────────────
    end = datetime.now(KST)
    logging.info('\n' + '=' * 52)
    logging.info(f'  완료: {end.strftime("%H:%M")} KST')
    for r in results:
        logging.info(f'    {r}')
    logging.info('=' * 52)


if __name__ == '__main__':
    main()
