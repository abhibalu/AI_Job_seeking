"""
Correlation ID context for structured logging.

Uses ContextVar so each asyncio task / thread has its own value.
Set at request boundaries (middleware) and worker entry points.
"""
import logging
import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(cid: str | None) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def new_request_id() -> str:
    return str(uuid.uuid4())[:8]


class CorrelationFilter(logging.Filter):
    """Injects correlation_id into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get() or "-"
        return True
