"""GET /orders/{orderId} — fetch a single order."""

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
        user_id = require_header(headers, "X-User-Id")
    except AppError as err:
        return error_from_app_error(err)

    order_id = path_param(event, "orderId")
    if not order_id:
        return error_from_app_error(
            AppError("INVALID_PATH", "orderId is required", 400)
        )

    log_structured(
        logger,
        "order_fetch_requested",
        request_id=request_id,
        extra={"userId": user_id, "orderId": order_id},
    )

    repo = OrdersRepository(cfg.orders_table_name, cfg.idempotency_table_name)
    order = repo.get_order(order_id)
    if not order:
        return error_from_app_error(
            AppError("ORDER_NOT_FOUND", "Order not found", 404)
        )
    if order.get("userId") != user_id:
        log_structured(
            logger,
            "unauthorized_order_access",
            request_id=request_id,
            extra={"userId": user_id, "orderId": order_id},
        )
        return error_from_app_error(
            AppError(
                "FORBIDDEN",
                "You do not have access to this order",
                403,
            )
        )

    return success_response(200, _serialize(order))
