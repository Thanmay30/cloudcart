"""API Gateway HTTP API (v2) event helpers."""

from __future__ import annotations

import base64
import json
from typing import Any

from shared.errors import AppError


def parse_json_body(event: dict[str, Any]) -> Any:
    raw = event.get("body")
    if raw is None or raw == "":
        return None
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError(
            code="INVALID_JSON",
            message="Request body is not valid JSON",
            status_code=400,
        ) from exc


def path_param(event: dict[str, Any], name: str) -> str | None:
    params = event.get("pathParameters") or {}
    val = params.get(name)
    return str(val) if val is not None else None


def request_id_from_event(event: dict[str, Any]) -> str | None:
    ctx = event.get("requestContext", {})
    return ctx.get("requestId")
