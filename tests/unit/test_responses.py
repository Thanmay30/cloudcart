from __future__ import annotations

import json

from shared.errors import AppError
from shared.responses import error_from_app_error, success_response


def test_success_response_shape() -> None:
    resp = success_response(200, {"a": 1})
    body = json.loads(resp["body"])
    assert body["success"] is True
    assert body["data"]["a"] == 1


def test_error_from_app_error_shape() -> None:
    resp = error_from_app_error(AppError("X", "msg", 404))
    body = json.loads(resp["body"])
    assert body["success"] is False
    assert body["error"]["code"] == "X"
