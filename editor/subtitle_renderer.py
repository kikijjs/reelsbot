"""
자막 렌더링 모듈.

MoviePy TextClip을 이용해 subtitle_timeline 기반으로
각 자막을 지정 시간에 영상에 합성한다.
"""
import logging
from pathlib import Path

from moviepy import TextClip, CompositeVideoClip, VideoFileClip

logger = logging.getLogger(__name__)

# 기본 폰트 경로 후보 (한글 지원)
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _find_font() -> str:
    """사용 가능한 한글 폰트를 찾아 경로를 반환한다."""
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return path
    return "DejaVu-Sans"


def build_subtitle_clips(
    subtitle_timeline: list[dict],
    video_width: int,
    video_height: int,
    font_size: int = 52,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
) -> list[TextClip]:
    """
    subtitle_timeline을 받아 MoviePy TextClip 리스트를 생성한다.

    Args:
        subtitle_timeline: [{text, start_sec, end_sec}, ...] 리스트
        video_width: 영상 너비 (px)
        video_height: 영상 높이 (px)

    Returns:
        배치된 TextClip 리스트 (MoviePy 2.x with_* API 사용)
    """
    font = _find_font()
    clips: list[TextClip] = []

    for cue in subtitle_timeline:
        text = cue.get("text", "").strip()
        start = float(cue.get("start_sec", 0))
        end = float(cue.get("end_sec", start + 2))

        if not text:
            continue

        duration = end - start
        txt_clip = (
            TextClip(
                font=font,
                text=text,
                font_size=font_size,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                method="caption",
                size=(int(video_width * 0.85), None),
                text_align="center",
                duration=duration,
            )
            .with_start(start)
            # 화면 하단 80% 위치
            .with_position(("center", int(video_height * 0.80)))
        )
        clips.append(txt_clip)
        logger.debug("자막 생성: %.1f~%.1f | %s", start, end, text[:20])

    logger.info("자막 클립 %d개 생성 완료", len(clips))
    return clips
