"""POST /orders — create order with idempotency and enqueue for processing."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from shared.api_gw import parse_json_body, request_id_from_event
from shared.config import AppConfig, require_config_for_api
from shared.errors import AppError
from shared.idempotency import idempotency_ttl_epoch_seconds
from shared.logging import get_logger, log_structured
from shared.orders_repository import OrdersRepository, now_iso
from shared.responses import error_response, error_from_app_error, success_response
from shared.sqs import send_order_processing_message
from shared.validation import parse_create_order_body, require_header, total_amount

logger = get_logger(__name__)


def _serialize_order(order: dict[str, Any]) -> dict[str, Any]:
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
    missing = require_config_for_api(cfg)
    if missing:
        log_structured(
            logger,
            "order_create_requested",
            request_id=request_id,
            extra={"error": "misconfigured", "missing": missing},
        )
        return error_response(
            500, "INTERNAL_ERROR", "Service misconfigured"
        )

    headers = event.get("headers") or {}
    try:
        user_id = require_header(headers, "X-User-Id")
        idem_key = require_header(headers, "Idempotency-Key")
        body = parse_json_body(event)
        parsed = parse_create_order_body(body)
        items = parsed["items"]
        total = total_amount(items)
        items_for_store = [
            {
                "productId": i["productId"],
                "name": i["name"],
                "quantity": i["quantity"],
                "unitPrice": Decimal(str(i["unitPrice"])),
            }
            for i in items
        ]
    except AppError as err:
        return error_from_app_error(err)

    log_structured(
        logger,
        "order_create_requested",
        request_id=request_id,
        extra={"userId": user_id},
    )

    repo = OrdersRepository(cfg.orders_table_name, cfg.idempotency_table_name)
    created_at = now_iso()
    order_id = str(uuid.uuid4())
    order = {
        "orderId": order_id,
        "userId": user_id,
        "items": items_for_store,
        "totalAmount": Decimal(total),
        "status": "PAYMENT_PENDING",
        "idempotencyKey": idem_key,
        "createdAt": created_at,
        "updatedAt": created_at,
        "failureReason": None,
        "attemptCount": 0,
    }

    expires_at = idempotency_ttl_epoch_seconds(7)
    try:
        created = repo.transact_create_order_and_idempotency(
            order=order,
            user_id=user_id,
            idempotency_key=idem_key,
            created_at=created_at,
            expires_at=expires_at,
        )
    except Exception as exc:  # noqa: BLE001 — surface as 500
        log_structured(
            logger,
            "order_create_requested",
            request_id=request_id,
            extra={"userId": user_id, "error": str(exc)},
        )
        return error_response(
            500, "INTERNAL_ERROR", "Unexpected error creating order"
        )

    if not created:
        record = repo.get_idempotency_record(user_id, idem_key)
        if not record:
            return error_response(
                500, "IDEMPOTENCY_CONFLICT", "Could not resolve idempotency record"
            )
        existing = repo.get_order(str(record["orderId"]))
        if not existing:
            return error_response(500, "ORDER_NOT_FOUND", "Original order missing")
        log_structured(
            logger,
            "duplicate_idempotency_key",
            request_id=request_id,
            extra={
                "userId": user_id,
                "orderId": existing.get("orderId"),
                "status": existing.get("status"),
            },
        )
        data = _serialize_order(existing)
        data["idempotentReplay"] = True
        return success_response(200, data)

    log_structured(
        logger,
        "order_created",
        request_id=request_id,
        extra={
            "userId": user_id,
            "orderId": order_id,
            "status": "PAYMENT_PENDING",
        },
    )

    msg = {
        "orderId": order_id,
        "userId": user_id,
        "totalAmount": float(Decimal(total)),
        "createdAt": created_at,
    }
    try:
        send_order_processing_message(cfg.order_processing_queue_url, msg)
    except Exception as exc:  # noqa: BLE001
        log_structured(
            logger,
            "order_created",
            request_id=request_id,
            extra={"orderId": order_id, "sqsError": str(exc)},
        )
        return error_response(
            500, "ENQUEUE_FAILED", "Order created but processing queue unavailable"
        )

    fresh = repo.get_order(order_id) or order
    data = _serialize_order(fresh)
    data["idempotentReplay"] = False
    return success_response(201, data)
