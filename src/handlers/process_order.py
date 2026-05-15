"""SQS-triggered payment simulation and order status updates."""

from __future__ import annotations

import json
from typing import Any

from botocore.exceptions import ClientError

from shared.config import AppConfig
from shared.errors import AppError
from shared.logging import get_logger, log_structured
from shared.orders_repository import OrdersRepository, now_iso
from shared.payment import simulate_payment

logger = get_logger(__name__)


class RetryableProcessingError(Exception):
    """Raised to return the SQS message to the queue for another attempt."""


def _process_record(record: dict[str, Any], request_id: str | None) -> None:
    cfg = AppConfig.from_environ()
    if not cfg.orders_table_name:
        raise RuntimeError("ORDERS_TABLE_NAME is not set")

    try:
        body = json.loads(record.get("body") or "{}")
    except json.JSONDecodeError as exc:
        log_structured(
            logger,
            "sqs_message_parse_failed",
            request_id=request_id,
            extra={"error": str(exc)},
        )
        raise

    order_id = str(body.get("orderId") or "")
    user_id = str(body.get("userId") or "")
    if not order_id or not user_id:
        log_structured(
            logger,
            "sqs_message_parse_failed",
            request_id=request_id,
            extra={"orderId": order_id, "userId": user_id},
        )
        raise ValueError("Invalid SQS message body")

    repo = OrdersRepository(
        cfg.orders_table_name,
        cfg.idempotency_table_name or cfg.orders_table_name,
    )
    order = repo.get_order(order_id)
    if not order:
        log_structured(
            logger,
            "order_missing",
            request_id=request_id,
            extra={"orderId": order_id, "userId": user_id},
        )
        raise RuntimeError("Order not found for SQS message")

    status = str(order.get("status", ""))
    if status in {"CANCELLED", "DELIVERED", "PAID"}:
        log_structured(
            logger,
            "skipped_order",
            request_id=request_id,
            extra={"orderId": order_id, "userId": user_id, "status": status},
        )
        return

    if status != "PAYMENT_PENDING":
        log_structured(
            logger,
            "skipped_order",
            request_id=request_id,
            extra={"orderId": order_id, "userId": user_id, "status": status},
        )
        return

    attempt_count = int(order.get("attemptCount") or 0)
    log_structured(
        logger,
        "payment_processing_started",
        request_id=request_id,
        extra={
            "orderId": order_id,
            "userId": user_id,
            "status": status,
            "attemptCount": attempt_count,
        },
    )

    outcome = simulate_payment(
        order_id=order_id,
        attempt_count=attempt_count,
        payment_failure_rate=cfg.payment_failure_rate,
        payment_force_result=cfg.payment_force_result,
    )

    updated_at = now_iso()

    if outcome == "success":
        try:
            repo.mark_payment_succeeded(order_id, updated_at=updated_at)
        except AppError as err:
            if err.code == "ORDER_STATE_CONFLICT":
                log_structured(
                    logger,
                    "skipped_order",
                    request_id=request_id,
                    extra={"orderId": order_id, "userId": user_id, "reason": "state_changed"},
                )
                return
            raise
        log_structured(
            logger,
            "payment_succeeded",
            request_id=request_id,
            extra={"orderId": order_id, "userId": user_id, "status": "PAID"},
        )
        return

    if outcome == "permanent_failure":
        try:
            repo.mark_payment_failed_permanent(
                order_id,
                updated_at=updated_at,
                failure_reason="payment_declined",
                increment_attempt=True,
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                log_structured(
                    logger,
                    "skipped_order",
                    request_id=request_id,
                    extra={"orderId": order_id, "userId": user_id, "reason": "not_pending"},
                )
                return
            raise
        log_structured(
            logger,
            "payment_failed",
            request_id=request_id,
            extra={
                "orderId": order_id,
                "userId": user_id,
                "retryable": False,
                "status": "FAILED",
            },
        )
        return

    # retryable_failure
    try:
        repo.add_attempt_count(order_id, updated_at=updated_at)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            log_structured(
                logger,
                "skipped_order",
                request_id=request_id,
                extra={"orderId": order_id, "userId": user_id, "reason": "not_pending"},
            )
            return
        raise

    log_structured(
        logger,
        "payment_failed",
        request_id=request_id,
        extra={
            "orderId": order_id,
            "userId": user_id,
            "retryable": True,
            "status": "PAYMENT_PENDING",
        },
    )
    raise RetryableProcessingError("Payment failed; retry requested")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", None)
    for record in event.get("Records", []):
        _process_record(record, request_id)
    return {"ok": True}
