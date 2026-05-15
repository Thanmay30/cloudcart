"""Structured JSON-style logs for CloudWatch."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_structured(
    logger: logging.Logger,
    event: str,
    *,
    request_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if request_id:
        payload["requestId"] = request_id
    if extra:
        for k, v in extra.items():
            if v is not None:
                payload[k] = v
    logger.info(json.dumps(payload, default=str))
