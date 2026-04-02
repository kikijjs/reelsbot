"""
YouTube Shorts 업로드 모듈 (YouTube Data API v3).

업로드 흐름:
  1. OAuth2 refresh_token으로 access_token 갱신
  2. resumable upload로 MP4 업로드
  3. 업로드 완료 후 video_id, URL 반환

공식 문서: https://developers.google.com/youtube/v3/guides/uploading_a_video
"""
import logging
from pathlib import Path

import httpx

from config import settings
from publisher.schemas import PlatformMeta, UploadResult

logger = logging.getLogger(__name__)

_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
_CHUNK_SIZE = 8 * 1024 * 1024   # 8 MB


def _refresh_access_token() -> str:
    """refresh_token으로 YouTube access_token을 갱신한다."""
    resp = httpx.post(
        _OAUTH_TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.youtube_refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"access_token 갱신 실패: {resp.json()}")
    logger.info("YouTube access_token 갱신 완료")
    return token


def _initiate_resumable_upload(access_token: str, meta: PlatformMeta, file_size: int) -> str:
    """Resumable Upload 세션을 시작하고 upload_url을 반환한다."""
    description = meta.description
    if meta.hashtags:
        description += "\n" + " ".join(meta.hashtags)

    resp = httpx.post(
        _UPLOAD_URL,
        params={
            "uploadType": "resumable",
            "part": "snippet,status",
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(file_size),
        },
        json={
            "snippet": {
                "title": meta.title,
                "description": description,
                "tags": meta.tags,
                "categoryId": "22",   # People & Blogs
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    upload_url = resp.headers.get("Location")
    if not upload_url:
        raise RuntimeError("Resumable upload URL 없음")
    logger.info("YouTube 업로드 세션 시작")
    return upload_url


def _upload_file(upload_url: str, video_path: str, file_size: int) -> str:
    """청크 단위로 파일을 업로드하고 video_id를 반환한다."""
    with open(video_path, "rb") as f:
        start = 0
        while start < file_size:
            chunk = f.read(_CHUNK_SIZE)
            end = start + len(chunk) - 1

            resp = httpx.put(
                upload_url,
                content=chunk,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Type": "video/mp4",
                },
                timeout=120,
            )

            if resp.status_code in (200, 201):
                video_id = resp.json().get("id")
                logger.info("YouTube 업로드 완료: video_id=%s", video_id)
                return video_id

            if resp.status_code == 308:
                # Resume Incomplete — 다음 청크로 계속
                range_header = resp.headers.get("Range", f"bytes=0-{end}")
                start = int(range_header.split("-")[1]) + 1
                logger.debug("YouTube 청크 업로드 진행: %d/%d bytes", start, file_size)
                continue

            resp.raise_for_status()

    raise RuntimeError("YouTube 파일 업로드 완료 후 video_id를 받지 못함")


def upload_short(video_path: str, meta: PlatformMeta) -> UploadResult:
    """
    YouTube Shorts를 업로드한다.

    Args:
        video_path: 로컬 MP4 파일 경로
        meta: 제목/설명/태그 메타데이터

    Returns:
        UploadResult
    """
    try:
        file_size = Path(video_path).stat().st_size
        access_token = _refresh_access_token()
        upload_url = _initiate_resumable_upload(access_token, meta, file_size)
        video_id = _upload_file(upload_url, video_path, file_size)

        post_url = f"https://www.youtube.com/shorts/{video_id}"
        return UploadResult(
            platform="youtube",
            success=True,
            post_id=video_id,
            post_url=post_url,
        )
    except Exception as e:
        logger.error("YouTube 업로드 실패: %s", e)
        return UploadResult(
            platform="youtube",
            success=False,
            error_message=str(e),
        )
