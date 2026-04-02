"""
각 플랫폼 API에서 업로드된 영상의 성과 지표를 수집하는 모듈.

플랫폼별 조회수·좋아요·댓글·공유 수를 반환한다.
"""
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _fetch_instagram_metrics(post_id: str) -> dict:
    """Instagram Graph API에서 Reels 성과 지표를 가져온다."""
    try:
        resp = httpx.get(
            f"https://graph.instagram.com/v21.0/{post_id}/insights",
            params={
                "metric": "plays,likes,comments,shares",
                "access_token": settings.meta_access_token,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = {item["name"]: item["values"][0]["value"] for item in resp.json().get("data", [])}
        return {
            "views": data.get("plays", 0),
            "likes": data.get("likes", 0),
            "comments": data.get("comments", 0),
            "shares": data.get("shares", 0),
        }
    except Exception as e:
        logger.warning("Instagram 지표 수집 실패 (무시): %s", e)
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0}


def _fetch_youtube_metrics(video_id: str) -> dict:
    """YouTube Data API v3에서 Shorts 성과 지표를 가져온다."""
    try:
        # access_token 갱신
        token_resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": settings.youtube_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        resp = httpx.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "statistics",
                "id": video_id,
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return {"views": 0, "likes": 0, "comments": 0, "shares": 0}
        stats = items[0].get("statistics", {})
        return {
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "shares": 0,  # YouTube API는 공유 수를 공개하지 않음
        }
    except Exception as e:
        logger.warning("YouTube 지표 수집 실패 (무시): %s", e)
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0}


def _fetch_tiktok_metrics(publish_id: str) -> dict:
    """TikTok Research API에서 영상 성과 지표를 가져온다."""
    try:
        resp = httpx.post(
            "https://open.tiktokapis.com/v2/video/query/",
            headers={
                "Authorization": f"Bearer {settings.tiktok_access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "filters": {"video_ids": [publish_id]},
                "fields": ["view_count", "like_count", "comment_count", "share_count"],
            },
            timeout=15,
        )
        resp.raise_for_status()
        videos = resp.json().get("data", {}).get("videos", [])
        if not videos:
            return {"views": 0, "likes": 0, "comments": 0, "shares": 0}
        v = videos[0]
        return {
            "views": v.get("view_count", 0),
            "likes": v.get("like_count", 0),
            "comments": v.get("comment_count", 0),
            "shares": v.get("share_count", 0),
        }
    except Exception as e:
        logger.warning("TikTok 지표 수집 실패 (무시): %s", e)
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0}


def fetch_metrics(platform: str, post_id: str) -> dict:
    """플랫폼 이름에 맞는 지표 수집 함수를 호출한다."""
    fetchers = {
        "instagram": _fetch_instagram_metrics,
        "youtube": _fetch_youtube_metrics,
        "tiktok": _fetch_tiktok_metrics,
    }
    fn = fetchers.get(platform)
    if fn is None:
        logger.warning("알 수 없는 플랫폼: %s", platform)
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0}
    return fn(post_id)
