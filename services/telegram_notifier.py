"""
Telegram Notifier — sends push alerts for pipeline events.

Uses the Bot API via httpx (sync). No dependencies on python-telegram-bot library.
Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to enable.
"""
import logging
import json

import httpx

from backend.settings import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
_ENABLED = bool(getattr(settings, "TELEGRAM_BOT_TOKEN", "") and getattr(settings, "TELEGRAM_CHAT_ID", ""))


def _send(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to the configured Telegram chat. Returns True on success."""
    if not _ENABLED:
        logger.debug(f"[Telegram] Notification skipped (not configured): {text[:80]}")
        return False
    try:
        url = f"{TELEGRAM_API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": parse_mode,
        }
        resp = httpx.post(url, json=payload, timeout=10)
        if not resp.is_success:
            logger.warning(f"[Telegram] Send failed: {resp.status_code} {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        logger.warning("[Telegram] Send error: %s", e, exc_info=True)
        return False


# -------------------------------------------------------------------
# Named alert types (keeps callers expressive, not raw HTML strings)
# -------------------------------------------------------------------

def notify_scrape_complete(jobs_found: int, jobs_new: int, search_url: str) -> None:
    """Alert: scheduled scrape finished."""
    icon = "🕷️"
    text = (
        f"{icon} <b>Scrape Complete</b>\n"
        f"Found <b>{jobs_found}</b> jobs | <b>{jobs_new}</b> new\n"
        f"<i>{search_url[:80]}</i>"
    )
    _send(text)


def notify_scrape_failed(error: str, search_url: str) -> None:
    """Alert: scrape worker crashed."""
    text = (
        f"❌ <b>Scraper Failed</b>\n"
        f"<code>{error[:300]}</code>\n"
        f"<i>URL: {search_url[:60]}</i>"
    )
    _send(text)


def notify_eval_complete(total: int, applied: int, tailored: int, skipped: int) -> None:
    """Alert: evaluation batch done."""
    text = (
        f"🤖 <b>Evaluation Batch Done</b>\n"
        f"Processed: <b>{total}</b> | Apply: <b>{applied}</b> | Tailor: <b>{tailored}</b> | Skip: <b>{skipped}</b>"
    )
    _send(text)


def notify_high_match(company: str, title: str, score: int, job_id: str, action: str) -> None:
    """Alert: a job scored ≥70 and is worth reviewing."""
    icon = "🔥" if score >= 80 else "✨"
    text = (
        f"{icon} <b>High Match Found!</b>\n"
        f"<b>{score}/100</b> — {title} @ {company}\n"
        f"Action: <code>{action}</code>\n"
        f"Job ID: <code>{job_id}</code>"
    )
    _send(text)


def notify_pipeline_error(stage: str, error: str) -> None:
    """Alert: any unhandled pipeline error."""
    text = (
        f"🚨 <b>Pipeline Error</b> in <b>{stage}</b>\n"
        f"<code>{error[:400]}</code>"
    )
    _send(text)
