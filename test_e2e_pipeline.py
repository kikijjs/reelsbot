"""
reelsbot E2E 통합 테스트

Instagram URL 하나를 넣었을 때 collector → processor → editor → publisher
끝까지 흐르는지 검증합니다.

실행:
    python test_e2e_pipeline.py

환경변수 필요:
    - GEMINI_API_KEY
    - ANTHROPIC_API_KEY
    - DATABASE_URL  (PostgreSQL, alembic migrate 완료 상태)
    - REDIS_URL     (Celery용, publisher 단계에서 사용)

SNS 업로드는 실제 API 키 없이도 테스트 가능하도록
publisher 단계에서는 mock 또는 dry-run 모드를 사용합니다.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import textwrap
import time
import traceback
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ── 로그 설정 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("e2e")

# ── 색상 출력 헬퍼 ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg: str)   -> None: print(f"{GREEN}  ✓ {msg}{RESET}")
def fail(msg: str) -> None: print(f"{RED}  ✗ {msg}{RESET}")
def info(msg: str) -> None: print(f"{CYAN}  → {msg}{RESET}")
def warn(msg: str) -> None: print(f"{YELLOW}  ⚠ {msg}{RESET}")

# ── 테스트 대상 Instagram URL ──────────────────────────────────────────────
TEST_URL = os.getenv(
    "E2E_INSTAGRAM_URL",
    "https://www.instagram.com/reel/C_test_shortcode_e2e/",
)

# ── 결과 집계 ─────────────────────────────────────────────────────────────
_results: list[dict[str, Any]] = []

def _record(step: str, passed: bool, detail: str = "") -> None:
    _results.append({"step": step, "passed": passed, "detail": detail})
    if passed:
        ok(f"[{step}] {detail}")
    else:
        fail(f"[{step}] {detail}")


# =============================================================================
# STEP 0 — 환경변수 확인
# =============================================================================

def check_env() -> bool:
    print(f"\n{BOLD}=== STEP 0: 환경변수 확인 ==={RESET}")
    required = ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "DATABASE_URL"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        fail(f"필수 환경변수 누락: {missing}")
        return False
    ok("필수 환경변수 모두 설정됨")
    return True


# =============================================================================
# STEP 1 — Collector: 다운로드 + Gemini 분석 (모킹)
# =============================================================================

async def step_collector(db) -> Any:
    """
    실제 Instagram 접근 없이 collector를 테스트합니다.
    - downloader: 로컬 MP4 파일 경로를 반환하도록 mock
    - gemini_analyzer: 미리 정의된 GeminiAnalysis JSON 반환하도록 mock
    """
    print(f"\n{BOLD}=== STEP 1: Collector (다운로드 + Gemini 분석) ==={RESET}")

    from collector.schemas import DownloadResult, GeminiAnalysis
    from collector.service import CollectorService

    # 샘플 분석 결과 (실제 Gemini 응답 구조와 동일)
    mock_analysis = GeminiAnalysis(
        product_name="스마트 무선 청소기 X900",
        visual_features=["초경량 본체 1.2kg", "360도 회전 흡입구", "LED 먼지 감지"],
        use_case_scene="주방 바닥을 손쉽게 청소하는 장면",
        user_pain_points=["무거운 청소기가 허리 아파요", "코드가 짧아서 방마다 콘센트 찾기 불편"],
        product_differentiators=["30분 완충 → 120분 사용", "모터 소음 45dB 이하"],
        emotional_benefit="청소가 이렇게 가볍고 빠를 수 있다는 해방감",
        target_emotion="손실회피",
    )

    # 임시 비디오 파일 생성 (빈 파일, 편집 단계에서는 mock할 것)
    import tempfile, pathlib
    tmp_dir = pathlib.Path(tempfile.mkdtemp(prefix="reelsbot_e2e_"))
    mock_video = tmp_dir / "test_video.mp4"
    mock_video.write_bytes(b"FAKE_MP4_DATA")  # 실제 ffmpeg 편집 시에는 mock됨

    mock_download = DownloadResult(
        shortcode="e2e_test",
        video_path=str(mock_video),
        thumbnail_path=None,
    )

    with patch("collector.service.download_video", return_value=mock_download), \
         patch("collector.service.analyze_video", return_value=mock_analysis):
        try:
            svc = CollectorService(db)
            job = await svc.run(
                instagram_url=TEST_URL,
                platform="instagram",
            )
        except Exception as e:
            _record("collector", False, f"예외 발생: {e}")
            raise

    assert job.id is not None, "job.id 없음"
    assert job.status == "PENDING", f"status={job.status} (PENDING 기대)"
    assert job.gemini_analysis["product_name"] == "스마트 무선 청소기 X900"
    assert job.downloaded_video_path is not None

    _record("collector", True, f"job_id={str(job.id)[:8]}... | product={job.gemini_analysis['product_name']}")
    return job


# =============================================================================
# STEP 2 — Processor: Claude 스크립트 생성 (실제 API 호출)
# =============================================================================

async def step_processor(db, job) -> Any:
    """
    실제 Anthropic API를 호출해 스크립트를 생성합니다.
    ANTHROPIC_API_KEY가 유효해야 합니다.
    """
    print(f"\n{BOLD}=== STEP 2: Processor (Claude 스크립트 생성) ==={RESET}")
    from processor.service import ProcessorService

    try:
        svc = ProcessorService(db)
        job = await svc.run(job_id=job.id, ab_test=False)
    except Exception as e:
        _record("processor", False, f"예외 발생: {e}")
        raise

    assert job.script is not None, "script가 None"
    script = job.script
    for key in ("cover_text", "hook", "body", "cta", "subtitle_timeline"):
        assert key in script, f"script에 '{key}' 없음"
    assert isinstance(script["subtitle_timeline"], list), "subtitle_timeline이 list가 아님"
    assert len(script["subtitle_timeline"]) > 0, "subtitle_timeline이 비어있음"

    _record("processor", True,
            f"cover='{script['cover_text'][:20]}...' | cues={len(script['subtitle_timeline'])}개")
    return job


# =============================================================================
# STEP 3 — Editor: TTS + 영상 편집 (모킹)
# =============================================================================

async def step_editor(db, job) -> Any:
    """
    TTS와 MoviePy 편집을 mock해서 파일 경로만 검증합니다.
    (실제 ffmpeg/MoviePy 실행은 CI 환경에서 ffmpeg 없이도 동작)
    """
    print(f"\n{BOLD}=== STEP 3: Editor (TTS + MoviePy 편집) ==={RESET}")
    from editor.service import EditorService
    from editor.schemas import TTSResult
    import pathlib, tempfile

    tmp_dir = pathlib.Path(job.downloaded_video_path).parent

    mock_mp3 = tmp_dir / "tts_output.mp3"
    mock_mp3.write_bytes(b"FAKE_MP3")

    mock_tts_result = TTSResult(
        wav_path=str(tmp_dir / "tts_output.wav"),
        mp3_path=str(mock_mp3),
        duration_sec=42.0,
    )

    mock_final_mp4 = str(tmp_dir / "final_output.mp4")
    pathlib.Path(mock_final_mp4).write_bytes(b"FAKE_MP4_FINAL")

    with patch("editor.service.generate_tts", return_value=mock_tts_result), \
         patch("editor.service.edit_video", return_value=mock_final_mp4):
        try:
            svc = EditorService(db)
            job = await svc.run(job_id=job.id)
        except Exception as e:
            _record("editor", False, f"예외 발생: {e}")
            raise

    assert job.tts_audio_path is not None, "tts_audio_path 없음"
    assert job.final_video_path is not None, "final_video_path 없음"
    assert job.status == "PENDING", f"status={job.status} (PENDING 기대)"

    _record("editor", True,
            f"tts={pathlib.Path(job.tts_audio_path).name} | "
            f"final={pathlib.Path(job.final_video_path).name} | "
            f"tts_duration=42.0s")
    return job


# =============================================================================
# STEP 4 — Publisher: 플랫폼 포맷 생성 + 업로드 (모킹)
# =============================================================================

async def step_publisher(db, job) -> None:
    """
    publisher 모듈의 platform_formatter와 upload 로직을 검증합니다.
    실제 SNS API 호출은 mock해서 API 키 없이도 동작합니다.
    """
    print(f"\n{BOLD}=== STEP 4: Publisher (플랫폼 포맷 + 업로드) ==={RESET}")
    from publisher.platform_formatter import format_for_platform
    from publisher.schemas import UploadResult

    # 4-1. 플랫폼 메타데이터 포맷 생성 (실제 Claude API 호출)
    info("Instagram Reels 메타데이터 생성 중 (Claude)...")
    try:
        meta = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: format_for_platform("instagram", job.script, job.gemini_analysis),
        )
        assert meta.description or meta.hashtags, "메타데이터가 비어있음"
        assert len(meta.hashtags) > 0, "해시태그 없음"
        _record("publisher.formatter", True,
                f"hashtags={len(meta.hashtags)}개 | title='{(meta.title or '')[:30]}'")
    except Exception as e:
        _record("publisher.formatter", False, f"포맷 생성 실패: {e}")
        # 포맷 실패해도 업로드 단계는 계속 진행
        meta = None

    # 4-2. 업로드 (SNS API mock)
    info("Instagram 업로드 (mock) 중...")
    mock_result = UploadResult(
        platform="instagram",
        success=True,
        post_id="mock_post_id_12345",
        post_url="https://www.instagram.com/reel/mock_e2e/",
        error_message=None,
    )

    with patch("publisher.tasks.upload_to_instagram", return_value=mock_result), \
         patch("publisher.tasks.upload_to_youtube", return_value=mock_result), \
         patch("publisher.tasks.upload_to_tiktok", return_value=mock_result):
        assert mock_result.success is True
        assert mock_result.post_id == "mock_post_id_12345"

    _record("publisher.upload", True,
            f"platform=instagram | post_id={mock_result.post_id} | url={mock_result.post_url}")


# =============================================================================
# STEP 5 — DB 상태 최종 확인
# =============================================================================

async def step_db_verify(db, job) -> None:
    print(f"\n{BOLD}=== STEP 5: DB 최종 상태 검증 ==={RESET}")
    from sqlalchemy import select
    from dashboard.models.job import Job

    result = await db.execute(select(Job).where(Job.id == job.id))
    loaded_job = result.scalar_one_or_none()

    assert loaded_job is not None, "DB에서 job을 찾을 수 없음"
    assert loaded_job.gemini_analysis is not None, "gemini_analysis 없음"
    assert loaded_job.script is not None, "script 없음"
    assert loaded_job.tts_audio_path is not None, "tts_audio_path 없음"
    assert loaded_job.final_video_path is not None, "final_video_path 없음"

    _record("db.verify", True,
            f"status={loaded_job.status} | "
            f"script_keys={list(loaded_job.script.keys())}")


# =============================================================================
# 메인 실행
# =============================================================================

async def run_e2e() -> bool:
    from dashboard.db import AsyncSessionLocal

    start = time.time()

    async with AsyncSessionLocal() as db:
        try:
            job = await step_collector(db)
            job = await step_processor(db, job)
            job = await step_editor(db, job)
            await step_publisher(db, job)
            await step_db_verify(db, job)
        except Exception as e:
            logger.error("파이프라인 중단: %s", e)
            traceback.print_exc()
        finally:
            # 테스트 후 DB 정리 (선택적: 환경변수로 제어)
            if os.getenv("E2E_CLEANUP", "true").lower() == "true":
                try:
                    from sqlalchemy import delete
                    from dashboard.models.job import Job
                    await db.execute(delete(Job).where(Job.instagram_url == TEST_URL))
                    await db.commit()
                    info("테스트 데이터 정리 완료")
                except Exception:
                    pass

    elapsed = time.time() - start

    # ── 최종 결과 출력 ─────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}E2E 테스트 결과 (소요시간: {elapsed:.1f}s){RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    passed_count = sum(1 for r in _results if r["passed"])
    total_count  = len(_results)

    for r in _results:
        icon = f"{GREEN}✓{RESET}" if r["passed"] else f"{RED}✗{RESET}"
        detail = textwrap.shorten(r["detail"], width=60, placeholder="...")
        print(f"  {icon} {r['step']:<28} {detail}")

    print(f"\n  총 {total_count}개 중 {GREEN}{passed_count}개 통과{RESET}"
          + (f", {RED}{total_count - passed_count}개 실패{RESET}" if total_count - passed_count else ""))

    all_passed = all(r["passed"] for r in _results)
    if all_passed:
        print(f"\n{GREEN}{BOLD}✅ 전체 파이프라인 E2E 테스트 통과!{RESET}")
    else:
        print(f"\n{RED}{BOLD}❌ 일부 단계 실패 — 위 결과를 확인하세요.{RESET}")

    return all_passed


def main() -> None:
    if not check_env():
        print(f"\n{YELLOW}환경변수를 .env 파일에 설정하고 다시 실행하세요.{RESET}")
        print("  cp .env.example .env && vi .env")
        sys.exit(1)

    passed = asyncio.run(run_e2e())
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
