"""
publisher 모듈 Pydantic 스키마.
"""
from typing import Literal
from pydantic import BaseModel, Field


class PlatformMeta(BaseModel):
    """플랫폼별 업로드 메타데이터."""

    title: str = Field(description="영상 제목")
    description: str = Field(description="영상 설명 / 캡션")
    hashtags: list[str] = Field(description="해시태그 목록 (# 포함)", default_factory=list)
    # YouTube 전용
    tags: list[str] = Field(description="YouTube 태그 목록", default_factory=list)
    # TikTok 전용
    trending_sound_id: str | None = Field(default=None, description="TikTok 트렌딩 사운드 ID")


class UploadResult(BaseModel):
    """플랫폼 업로드 결과."""

    platform: Literal["instagram", "youtube", "tiktok"]
    success: bool
    post_id: str | None = Field(default=None, description="업로드된 게시물 ID")
    post_url: str | None = Field(default=None, description="게시물 URL")
    error_message: str | None = Field(default=None)
