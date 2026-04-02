#!/bin/bash
# Celery 워커 + Beat 실행 스크립트
# 사용법: ./start_worker.sh [worker|beat|all]

MODE=${1:-all}
LOG_LEVEL=${LOG_LEVEL:-info}

case "$MODE" in
  worker)
    echo "[reelsbot] Celery 워커 시작..."
    celery -A publisher.celery_app worker \
      --loglevel=$LOG_LEVEL \
      --concurrency=4 \
      --pool=threads
    ;;
  beat)
    echo "[reelsbot] Celery Beat 스케줄러 시작..."
    celery -A publisher.celery_app beat \
      --loglevel=$LOG_LEVEL
    ;;
  all)
    echo "[reelsbot] Celery 워커 + Beat 동시 시작..."
    # 개발 환경 전용: 단일 프로세스로 워커+Beat 동시 실행
    celery -A publisher.celery_app worker \
      --beat \
      --loglevel=$LOG_LEVEL \
      --concurrency=4 \
      --pool=threads
    ;;
  *)
    echo "사용법: $0 [worker|beat|all]"
    exit 1
    ;;
esac
