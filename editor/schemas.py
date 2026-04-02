"""
editor 모듈 Pydantic 스키마.
"""
from pydantic import BaseModel, Field


class TTSPartConfig(BaseModel):
    """TTS 파트별 설정 (텍스트 + Style Instruction)."""

    text: str
    style_instruction: str
    part_name: str  # hook / body / cta


class TTSResult(BaseModel):
    """TTS 생성 결과."""

    wav_path: str
    mp3_path: str
    duration_sec: float


class EditConfig(BaseModel):
    """VideoEditor에 전달되는 편집 설정 전체."""

    source_video_path: str = Field(description="원본 인스타그램 MP4 경로")
    tts_audio_path: str = Field(description="합성된 TTS MP3 경로")
    cover_text: str = Field(description="커버 문구 (첫 3초 오버레이)")
    subtitle_timeline: list[dict] = Field(
        description="자막 타임라인 [{text, start_sec, end_sec}, ...]",
        default_factory=list,
    )
    output_path: str = Field(description="최종 MP4 출력 경로")
    # 출력 사양
    output_width: int = Field(default=1080)
    output_height: int = Field(default=1920)
    cover_duration_sec: float = Field(default=3.0, description="커버 문구 표시 시간")
