"""
processor 모듈 Pydantic 스키마.

Claude가 생성하는 5파트 스크립트 구조를 정의한다.
"""
from pydantic import BaseModel, Field


class SubtitleCue(BaseModel):
    """자막 타임라인의 단일 항목."""

    text: str = Field(description="자막 텍스트")
    start_sec: float = Field(description="자막 시작 시간(초)")
    end_sec: float = Field(description="자막 종료 시간(초)")


class Script5Parts(BaseModel):
    """Claude가 생성하는 5파트 한국어 숏폼 스크립트."""

    cover_text: str = Field(
        description="커버 문구(Thumbnail Text): 결핍·이득·호기심 중 하나를 건드려 1초 만에 클릭하게 만드는 텍스트"
    )
    hook: str = Field(
        description="후킹(Hook): 첫 3초 안에 시선 강탈. 질문형·충격적 사실·공감 불편함"
    )
    body: str = Field(
        description="공감 및 해결(Body): 제품 특징이 아닌 편익(Benefit)에 집중한 본문"
    )
    cta: str = Field(
        description="CTA(Call to Action): 댓글 유도 또는 프로필 링크 클릭 유도"
    )
    subtitle_timeline: list[SubtitleCue] = Field(
        description="각 파트별 자막 텍스트 + 권장 노출 시간(초) 리스트",
        default_factory=list,
    )


class ABTestScript(BaseModel):
    """A/B 테스트용 2버전 스크립트."""

    variant_a: Script5Parts = Field(description="A버전 — 손실회피 감정 전략")
    variant_b: Script5Parts = Field(description="B버전 — 이득강조 또는 호기심 감정 전략")
