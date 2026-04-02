"""
MoviePy 2.x 기반 영상 편집 모듈.

처리 순서:
  1. 원본 영상 로드 → 9:16 크롭/리사이즈 (1080×1920)
  2. 기존 오디오 제거
  3. TTS MP3 오디오 교체
  4. 커버 문구 오버레이 (첫 3초)
  5. 자막 클립 합성
  6. 최종 MP4 출력
"""
import logging
import subprocess
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    VideoFileClip,
)

from editor.schemas import EditConfig
from editor.subtitle_renderer import build_subtitle_clips
from editor.cover_overlay import build_cover_clip

logger = logging.getLogger(__name__)

TARGET_W = 1080
TARGET_H = 1920
TARGET_RATIO = TARGET_W / TARGET_H  # 9:16 = 0.5625


def _resize_to_916(clip: VideoFileClip) -> VideoFileClip:
    """
    영상을 9:16 세로형(1080×1920)으로 변환한다.

    - 원본이 가로형이면 중앙 크롭 후 리사이즈
    - 원본이 이미 세로형이면 리사이즈만
    """
    w, h = clip.size
    current_ratio = w / h

    if current_ratio > TARGET_RATIO:
        # 가로가 더 넓음 → 좌우 크롭
        new_w = int(h * TARGET_RATIO)
        x_center = w // 2
        clip = clip.cropped(
            x1=x_center - new_w // 2,
            x2=x_center + new_w // 2,
            y1=0,
            y2=h,
        )
    elif current_ratio < TARGET_RATIO:
        # 세로가 더 긺 → 상하 크롭
        new_h = int(w / TARGET_RATIO)
        y_center = h // 2
        clip = clip.cropped(
            x1=0,
            x2=w,
            y1=y_center - new_h // 2,
            y2=y_center + new_h // 2,
        )

    return clip.resized((TARGET_W, TARGET_H))


def edit_video(config: EditConfig) -> str:
    """
    EditConfig에 따라 영상을 편집하고 최종 MP4를 생성한다.

    Args:
        config: 편집 설정

    Returns:
        생성된 MP4 파일의 절대 경로
    """
    if not Path(config.source_video_path).exists():
        raise FileNotFoundError(f"원본 영상 없음: {config.source_video_path}")
    if not Path(config.tts_audio_path).exists():
        raise FileNotFoundError(f"TTS 오디오 없음: {config.tts_audio_path}")

    Path(config.output_path).parent.mkdir(parents=True, exist_ok=True)

    logger.info("=== 영상 편집 시작 ===")
    logger.info("원본: %s", config.source_video_path)
    logger.info("TTS : %s", config.tts_audio_path)
    logger.info("출력: %s", config.output_path)

    # ── 1. 원본 영상 로드 + 9:16 변환 ─────────────────────────
    logger.info("[1/5] 원본 영상 로드 및 9:16 리사이즈...")
    video = VideoFileClip(config.source_video_path, audio=False)
    video = _resize_to_916(video)
    video_duration = video.duration
    logger.info("  원본 길이: %.1fs | 변환 후 해상도: %s", video_duration, video.size)

    # ── 2. TTS 오디오 교체 ────────────────────────────────────
    logger.info("[2/5] TTS 오디오 교체...")
    tts_audio = AudioFileClip(config.tts_audio_path)
    tts_duration = tts_audio.duration

    # 영상/오디오 중 더 긴 쪽에 맞춤
    final_duration = max(tts_duration, video_duration)
    video = video.with_duration(final_duration).with_audio(tts_audio)
    logger.info("  TTS 길이: %.1fs | 최종 길이: %.1fs", tts_duration, final_duration)

    # ── 3. 커버 문구 오버레이 ─────────────────────────────────
    logger.info("[3/5] 커버 문구 오버레이 생성...")
    cover_clip = build_cover_clip(
        cover_text=config.cover_text,
        video_width=TARGET_W,
        video_height=TARGET_H,
        duration_sec=config.cover_duration_sec,
    )

    # ── 4. 자막 합성 ──────────────────────────────────────────
    logger.info("[4/5] 자막 클립 생성...")
    subtitle_clips = build_subtitle_clips(
        subtitle_timeline=config.subtitle_timeline,
        video_width=TARGET_W,
        video_height=TARGET_H,
    )

    # ── 5. 합성 + 출력 ────────────────────────────────────────
    logger.info("[5/5] 레이어 합성 및 MP4 인코딩...")
    all_clips = [video, cover_clip] + subtitle_clips
    final = CompositeVideoClip(all_clips, size=(TARGET_W, TARGET_H))
    final = final.with_duration(final_duration)

    final.write_videofile(
        config.output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        ffmpeg_params=["-crf", "23"],
        logger=None,
    )

    video.close()
    tts_audio.close()
    final.close()

    logger.info("=== 편집 완료: %s ===", config.output_path)
    return config.output_path
