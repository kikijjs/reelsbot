"""
Instagram 영상 다운로드 모듈.

instaloader를 사용해 Reel/Post URL에서 MP4를 다운로드한다.
로그인 없이 공개 게시물에만 동작한다.
"""
import re
import logging
from pathlib import Path

import instaloader

from config import settings
from collector.schemas import DownloadResult

logger = logging.getLogger(__name__)

# URL에서 shortcode 추출 패턴
# 지원 형식:
#   https://www.instagram.com/reel/ABC123/
#   https://www.instagram.com/p/ABC123/
_SHORTCODE_RE = re.compile(r"instagram\.com/(?:reel|p)/([A-Za-z0-9_\-]+)")


def _extract_shortcode(url: str) -> str:
    match = _SHORTCODE_RE.search(url)
    if not match:
        raise ValueError(f"Instagram URL에서 shortcode를 추출할 수 없습니다: {url}")
    return match.group(1)


def download_video(instagram_url: str) -> DownloadResult:
    """
    Instagram Reel/Post URL에서 영상을 다운로드한다.

    Returns:
        DownloadResult — shortcode와 저장된 MP4 경로
    Raises:
        ValueError: URL 형식이 올바르지 않을 때
        instaloader.exceptions.InstaloaderException: 다운로드 실패 시
    """
    shortcode = _extract_shortcode(instagram_url)

    # 저장 경로: {MEDIA_STORAGE_PATH}/{shortcode}/
    target_dir = Path(settings.media_storage_path) / shortcode
    target_dir.mkdir(parents=True, exist_ok=True)

    # 이미 다운로드된 파일이 있으면 재사용
    existing = list(target_dir.glob("*.mp4"))
    if existing:
        video_path = str(existing[0])
        logger.info("캐시된 영상 재사용: %s", video_path)
        return DownloadResult(
            instagram_url=instagram_url,
            video_path=video_path,
            shortcode=shortcode,
        )

    logger.info("Instagram 영상 다운로드 시작: shortcode=%s", shortcode)

    loader = instaloader.Instaloader(
        dirname_pattern=str(target_dir),
        filename_pattern="{shortcode}",
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        quiet=True,
    )

    post = instaloader.Post.from_shortcode(loader.context, shortcode)
    loader.download_post(post, target=target_dir)

    # 다운로드된 MP4 파일 탐색
    mp4_files = list(target_dir.glob("*.mp4"))
    if not mp4_files:
        raise FileNotFoundError(
            f"다운로드 완료 후 MP4 파일을 찾을 수 없습니다: {target_dir}"
        )

    video_path = str(mp4_files[0])
    logger.info("다운로드 완료: %s", video_path)

    return DownloadResult(
        instagram_url=instagram_url,
        video_path=video_path,
        shortcode=shortcode,
    )
