"""
Instagram Reels 업로드 모듈 (Meta Graph API).

업로드 흐름 (2단계 업로드):
  1. POST /me/media          — 컨테이너 생성 (creation_id 획득)
  2. 처리 완료 대기           — GET /{creation_id}?fields=status_code
  3. POST /me/media_publish  — 게시물 공개

공식 문서: https://developers.facebook.com/docs/instagram-api/guides/reels
"""
import logging
import time

import httpx

from config import settings
from publisher.schemas import PlatformMeta, UploadResult

logger = logging.getLogger(__name__)

_GRAPH = "https://graph.instagram.com/v21.0"

# 컨테이너 처리 완료 대기 설정
_POLL_INTERVAL = 5   # 초
_POLL_MAX = 120      # 최대 대기 시간 (초)


def _create_container(video_url: str, meta: PlatformMeta) -> str:
    """
    Reels 미디어 컨테이너를 생성하고 creation_id를 반환한다.

    Instagram Graph API는 공개 URL에서 직접 영상을 가져간다.
    로컬 파일은 먼저 공개 URL로 호스팅해야 한다.
    (실제 운영 시 S3/GCS에 업로드 후 URL 전달 권장)
    """
    caption = meta.description
    if meta.hashtags:
        caption += "\n\n" + " ".join(meta.hashtags[:30])

    resp = httpx.post(
        f"{_GRAPH}/{settings.meta_instagram_user_id}/media",
        params={"access_token": settings.meta_access_token},
        json={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": True,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    creation_id = data.get("id")
    if not creation_id:
        raise RuntimeError(f"creation_id 없음: {data}")
    logger.info("Instagram 컨테이너 생성: %s", creation_id)
    return creation_id


def _wait_for_container(creation_id: str) -> None:
    """컨테이너 처리가 완료될 때까지 폴링한다."""
    waited = 0
    while waited < _POLL_MAX:
        resp = httpx.get(
            f"{_GRAPH}/{creation_id}",
            params={
                "fields": "status_code,status",
                "access_token": settings.meta_access_token,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status_code", "")
        logger.info("Instagram 컨테이너 상태: %s (%ds)", status, waited)

        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram 컨테이너 처리 오류: {data}")

        time.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL

    raise TimeoutError(f"Instagram 컨테이너 처리 타임아웃 ({_POLL_MAX}초)")


def _publish_container(creation_id: str) -> str:
    """컨테이너를 공개 게시물로 발행하고 media_id를 반환한다."""
    resp = httpx.post(
        f"{_GRAPH}/{settings.meta_instagram_user_id}/media_publish",
        params={"access_token": settings.meta_access_token},
        json={"creation_id": creation_id},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    media_id = data.get("id")
    if not media_id:
        raise RuntimeError(f"media_id 없음: {data}")
    logger.info("Instagram 게시 완료: media_id=%s", media_id)
    return media_id


def upload_reel(video_url: str, meta: PlatformMeta) -> UploadResult:
    """
    Instagram Reels를 업로드한다.

    Args:
        video_url: 공개 접근 가능한 MP4 URL
        meta: 캡션 + 해시태그 메타데이터

    Returns:
        UploadResult
    """
    try:
        creation_id = _create_container(video_url, meta)
        _wait_for_container(creation_id)
        media_id = _publish_container(creation_id)

        post_url = f"https://www.instagram.com/p/{media_id}/"
        return UploadResult(
            platform="instagram",
            success=True,
            post_id=media_id,
            post_url=post_url,
        )
    except Exception as e:
        logger.error("Instagram 업로드 실패: %s", e)
        return UploadResult(
            platform="instagram",
            success=False,
            error_message=str(e),
        )
