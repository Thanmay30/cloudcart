"""API Gateway HTTP API (v2) response helpers."""

from __future__ import annotations

import json
from typing import Any

from shared.errors import AppError


def success_response(status_code: int, data: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"success": True, "data": data})
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": body,
    }


def error_response(status_code: int, code: str, message: str) -> dict[str, Any]:
    body = json.dumps(
        {"success": False, "error": {"code": code, "message": message}}
    )
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": body,
    }


def error_from_app_error(err: AppError) -> dict[str, Any]:
    return error_response(err.status_code, err.code, err.message)
