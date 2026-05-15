"""GET /orders/user/{userId} — list orders for a user."""

from __future__ import annotations

from typing import Any

from shared.api_gw import path_param, request_id_from_event
from shared.config import AppConfig, require_config_for_api
from shared.errors import AppError
from shared.logging import get_logger, log_structured
from shared.orders_repository import OrdersRepository
from shared.responses import error_from_app_error, success_response
from shared.validation import require_header

logger = get_logger(__name__)


def _serialize(order: dict[str, Any]) -> dict[str, Any]:
    from decimal import Decimal

    out = dict(order)
    ta = out.get("totalAmount")
    if isinstance(ta, Decimal):
        out["totalAmount"] = float(ta)
    items = out.get("items")
    if isinstance(items, list):
        new_items = []
        for it in items:
            if isinstance(it, dict):
                dit = dict(it)
                up = dit.get("unitPrice")
                if isinstance(up, Decimal):
                    dit["unitPrice"] = float(up)
                new_items.append(dit)
            else:
                new_items.append(it)
        out["items"] = new_items
    return out


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", None) or request_id_from_event(event)
    cfg = AppConfig.from_environ()
    if require_config_for_api(cfg):
        return error_from_app_error(
            AppError("INTERNAL_ERROR", "Service misconfigured", 500)
        )

    headers = event.get("headers") or {}
    try:
        caller_id = require_header(headers, "X-User-Id")
    except AppError as err:
        return error_from_app_error(err)

    path_uid = path_param(event, "userId")
    if not path_uid:
        return error_from_app_error(
            AppError("INVALID_PATH", "userId is required", 400)
        )

    if caller_id != path_uid:
        log_structured(
            logger,
            "unauthorized_order_access",
            request_id=request_id,
            extra={"userId": caller_id, "pathUserId": path_uid},
        )
        return error_from_app_error(
            AppError("FORBIDDEN", "Cannot list orders for another user", 403)
        )

    log_structured(
        logger,
        "order_fetch_requested",
        request_id=request_id,
        extra={"userId": caller_id, "list": True},
    )

    repo = OrdersRepository(cfg.orders_table_name, cfg.idempotency_table_name)
    orders = repo.query_orders_by_user(path_uid)
    return success_response(200, {"orders": [_serialize(o) for o in orders]})
