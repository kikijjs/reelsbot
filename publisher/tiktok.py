"""
TikTok 업로드 모듈 (TikTok Content Posting API v2).

업로드 흐름 (FILE_UPLOAD 방식):
  1. POST /v2/post/publish/video/init/   — 업로드 초기화, upload_url 획득
  2. PUT upload_url                      — 청크 업로드
  3. POST /v2/post/publish/status/fetch/ — 처리 완료 폴링
  4. publish_id로 TikTok 게시물 URL 구성

트렌딩 사운드:
  GET /v2/research/adlib/sound/list/    — 카테고리별 인기 사운드 목록 조회

공식 문서: https://developers.tiktok.com/doc/content-posting-api-get-started
"""
import logging
import time
from pathlib import Path

import httpx

from config import settings
from publisher.schemas import PlatformMeta, UploadResult

logger = logging.getLogger(__name__)

_API_BASE = "https://open.tiktokapis.com"
_CHUNK_SIZE = 10 * 1024 * 1024   # 10 MB
_POLL_INTERVAL = 5
_POLL_MAX = 120


# ── 트렌딩 사운드 추천 ──────────────────────────────────────────────

def get_trending_sounds(keyword: str = "", limit: int = 5) -> list[dict]:
    """
    TikTok Research API에서 트렌딩 사운드 목록을 조회한다.

    Args:
        keyword: 검색 키워드 (제품명 또는 카테고리)
        limit: 반환할 사운드 수

    Returns:
        [{"sound_id": "...", "title": "...", "author": "...", "usage_count": ...}, ...]
        API 키가 없거나 오류 시 빈 리스트 반환
    """
    if not settings.tiktok_access_token:
        logger.debug("TikTok 액세스 토큰 없음 — 트렌딩 사운드 건너뜀")
        return []

    try:
        resp = httpx.post(
            f"{_API_BASE}/v2/research/adlib/sound/list/",
            headers={
                "Authorization": f"Bearer {settings.tiktok_access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "filters": {
                    "keyword": keyword,
                    "region_code": "KR",
                },
                "max_count": limit,
                "cursor": 0,
            },
            timeout=15,
        )
        resp.raise_for_status()
        sounds = resp.json().get("data", {}).get("sounds", [])
        logger.info("트렌딩 사운드 %d개 조회", len(sounds))
        return [
            {
                "sound_id": s.get("id", ""),
                "title": s.get("title", ""),
                "author": s.get("author_name", ""),
                "usage_count": s.get("video_count", 0),
            }
            for s in sounds
        ]
    except Exception as e:
        logger.warning("트렌딩 사운드 조회 실패 (무시): %s", e)
        return []


# ── 업로드 핵심 로직 ────────────────────────────────────────────────

def _init_upload(video_path: str, meta: PlatformMeta) -> tuple[str, str]:
    """업로드를 초기화하고 (publish_id, upload_url)을 반환한다."""
    file_size = Path(video_path).stat().st_size
    total_chunks = (file_size + _CHUNK_SIZE - 1) // _CHUNK_SIZE

    caption = meta.description
    if meta.hashtags:
        caption += " " + " ".join(meta.hashtags[:10])

    body: dict = {
        "post_info": {
            "title": caption[:150],
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": _CHUNK_SIZE,
            "total_chunk_count": total_chunks,
        },
    }

    # 트렌딩 사운드 ID가 있으면 첨부
    if meta.trending_sound_id:
        body["post_info"]["music_id"] = meta.trending_sound_id

    resp = httpx.post(
        f"{_API_BASE}/v2/post/publish/video/init/",
        headers={
            "Authorization": f"Bearer {settings.tiktok_access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})
    publish_id = data.get("publish_id")
    upload_url = data.get("upload_url")

    if not publish_id or not upload_url:
        raise RuntimeError(f"TikTok 업로드 초기화 실패: {resp.json()}")

    logger.info("TikTok 업로드 초기화: publish_id=%s", publish_id)
    return publish_id, upload_url


def _upload_chunks(upload_url: str, video_path: str) -> None:
    """파일을 청크 단위로 업로드한다."""
    file_size = Path(video_path).stat().st_size

    with open(video_path, "rb") as f:
        chunk_index = 0
        uploaded = 0

        while uploaded < file_size:
            chunk = f.read(_CHUNK_SIZE)
            if not chunk:
                break

            end = uploaded + len(chunk) - 1
            resp = httpx.put(
                upload_url,
                content=chunk,
                headers={
                    "Content-Range": f"bytes {uploaded}-{end}/{file_size}",
                    "Content-Type": "video/mp4",
                },
                timeout=120,
            )

            if resp.status_code not in (200, 201, 206):
                resp.raise_for_status()

            uploaded += len(chunk)
            chunk_index += 1
            logger.debug(
                "TikTok 청크 %d 업로드: %d/%d bytes",
                chunk_index, uploaded, file_size,
            )

    logger.info("TikTok 파일 업로드 완료")


def _wait_for_publish(publish_id: str) -> str:
    """게시 처리 완료를 폴링하고 게시물 URL을 반환한다."""
    waited = 0
    while waited < _POLL_MAX:
        resp = httpx.post(
            f"{_API_BASE}/v2/post/publish/status/fetch/",
            headers={
                "Authorization": f"Bearer {settings.tiktok_access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        status = data.get("status", "")
        logger.info("TikTok 게시 상태: %s (%ds)", status, waited)

        if status == "PUBLISH_COMPLETE":
            # post_id 목록이 있으면 첫 번째 사용
            post_ids = data.get("publicaly_available_post_id", [])
            post_id = post_ids[0] if post_ids else publish_id
            return f"https://www.tiktok.com/@me/video/{post_id}"

        if status in ("FAILED", "PUBLISH_FAILED"):
            raise RuntimeError(f"TikTok 게시 실패: {data}")

        time.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL

    raise TimeoutError(f"TikTok 게시 타임아웃 ({_POLL_MAX}초)")


def upload_video(video_path: str, meta: PlatformMeta) -> UploadResult:
    """
    TikTok에 영상을 업로드한다.

    Args:
        video_path: 로컬 MP4 파일 경로
        meta: 캡션 + 해시태그 + 트렌딩 사운드 ID 메타데이터

    Returns:
        UploadResult
    """
    try:
        publish_id, upload_url = _init_upload(video_path, meta)
        _upload_chunks(upload_url, video_path)
        post_url = _wait_for_publish(publish_id)

        return UploadResult(
            platform="tiktok",
            success=True,
            post_id=publish_id,
            post_url=post_url,
        )
    except Exception as e:
        logger.error("TikTok 업로드 실패: %s", e)
        return UploadResult(
            platform="tiktok",
            success=False,
            error_message=str(e),
        )
