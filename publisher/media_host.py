"""
미디어 파일 공개 URL 호스팅 유틸리티.

Instagram Graph API는 로컬 파일 경로를 받지 않고 공개 접근 가능한 URL만 허용한다.
이 모듈은 운영 환경(S3/GCS)과 개발 환경(로컬 FastAPI 서빙)을 추상화한다.

운영 배포 시:
  - AWS S3, Google Cloud Storage, Cloudflare R2 등으로 교체
  - MEDIA_PUBLIC_BASE_URL 환경변수에 CDN URL 설정

개발 환경:
  - FastAPI의 /media 정적 파일 엔드포인트로 서빙
  - MEDIA_PUBLIC_BASE_URL=http://localhost:8000
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# 개발 기본값: localhost FastAPI 서버
_DEFAULT_BASE = "http://localhost:8000"


def get_public_url(local_path: str) -> str:
    """
    로컬 파일 경로를 공개 접근 가능한 URL로 변환한다.

    환경변수 MEDIA_PUBLIC_BASE_URL이 설정돼 있으면 해당 베이스 URL 사용.
    미설정 시 localhost:8000 기본값 사용.

    Args:
        local_path: 로컬 파일 경로 (예: ./media/ABC123/final_output.mp4)

    Returns:
        공개 URL (예: http://localhost:8000/media/ABC123/final_output.mp4)
    """
    base_url = os.getenv("MEDIA_PUBLIC_BASE_URL", _DEFAULT_BASE).rstrip("/")

    # ./media/ 접두어를 제거하고 상대 경로만 사용
    rel_path = Path(local_path)
    try:
        # media/ 폴더 기준 상대 경로 추출
        parts = rel_path.parts
        if "media" in parts:
            media_idx = list(parts).index("media")
            rel = "/".join(parts[media_idx:])
        else:
            rel = rel_path.name
    except Exception:
        rel = rel_path.name

    url = f"{base_url}/{rel}"
    logger.debug("공개 URL 변환: %s → %s", local_path, url)
    return url
