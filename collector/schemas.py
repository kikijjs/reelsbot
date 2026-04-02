from typing import Literal
from pydantic import BaseModel, Field


class GeminiAnalysis(BaseModel):
    """Gemini 1.5 Pro가 반환하는 영상 분석 결과."""

    product_name: str = Field(description="제품명 또는 주제")
    visual_features: list[str] = Field(
        description="시각적으로 보이는 주요 특징들", default_factory=list
    )
    use_case_scene: str = Field(description="영상에 나타난 사용 장면 묘사")
    user_pain_points: list[str] = Field(
        description="제품이 해결하는 사용자의 불편함/고통", default_factory=list
    )
    product_differentiators: list[str] = Field(
        description="경쟁 제품 대비 차별점", default_factory=list
    )
    emotional_benefit: str = Field(description="제품이 주는 정서적 혜택")
    target_emotion: Literal["손실회피", "이득강조", "호기심"] = Field(
        description="스크립트에서 자극할 감정 전략"
    )


class DownloadResult(BaseModel):
    """instaloader 다운로드 결과."""

    instagram_url: str
    video_path: str
    shortcode: str
