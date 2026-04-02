"""
Telegram 봇 알림 모듈.

업로드 성공/실패 시 지정된 chat_id로 메시지를 전송한다.
httpx로 동기 요청 (Celery 태스크 내부에서 호출되므로 동기).
"""
import logging
import httpx

from config import settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _send(text: str) -> None:
    """Telegram Bot API로 메시지를 전송한다."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        logger.debug("Telegram 설정이 없어 알림을 건너뜁니다.")
        return

    url = _TELEGRAM_API.format(token=token)
    try:
        resp = httpx.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Telegram 알림 전송 완료")
    except Exception as e:
        # 알림 실패는 치명적이지 않으므로 경고만 기록
        logger.warning("Telegram 알림 전송 실패 (무시): %s", e)


def notify_success(job_id: str, platform: str, post_url: str | None) -> None:
    url_line = f"\n🔗 {post_url}" if post_url else ""
    _send(
        f"✅ <b>업로드 완료</b>\n"
        f"플랫폼: <b>{platform.upper()}</b>\n"
        f"Job ID: <code>{job_id}</code>"
        f"{url_line}"
    )


def notify_failure(job_id: str, platform: str, error: str) -> None:
    _send(
        f"❌ <b>업로드 실패</b>\n"
        f"플랫폼: <b>{platform.upper()}</b>\n"
        f"Job ID: <code>{job_id}</code>\n"
        f"오류: <code>{error[:300]}</code>"
    )
