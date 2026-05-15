from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from handlers import process_order


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORDERS_TABLE_NAME", "orders")
    monkeypatch.setenv("IDEMPOTENCY_TABLE_NAME", "idem")
    monkeypatch.setenv("PAYMENT_FORCE_RESULT", "")


def test_process_order_success_updates_to_paid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYMENT_FORCE_RESULT", "success")
    order = {
        "orderId": "o1",
        "userId": "u1",
        "status": "PAYMENT_PENDING",
        "attemptCount": 0,
    }
    fake_repo = MagicMock()
    fake_repo.get_order.return_value = order

    event = {
        "Records": [
            {
                "body": json.dumps(
                    {"orderId": "o1", "userId": "u1", "totalAmount": 1.0, "createdAt": "t"}
                )
            }
        ]
    }

    with patch("handlers.process_order.OrdersRepository", return_value=fake_repo):
        process_order.handler(event, MagicMock(aws_request_id="r1"))

    fake_repo.mark_payment_succeeded.assert_called_once()


def test_process_order_retryable_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYMENT_FORCE_RESULT", "failure_retry")
    order = {
        "orderId": "o1",
        "userId": "u1",
        "status": "PAYMENT_PENDING",
        "attemptCount": 0,
    }
    fake_repo = MagicMock()
    fake_repo.get_order.return_value = order

    event = {
        "Records": [
            {
                "body": json.dumps(
                    {"orderId": "o1", "userId": "u1", "totalAmount": 1.0, "createdAt": "t"}
                )
            }
        ]
    }

    with patch("handlers.process_order.OrdersRepository", return_value=fake_repo):
        with pytest.raises(process_order.RetryableProcessingError):
            process_order.handler(event, MagicMock())

    fake_repo.add_attempt_count.assert_called_once()


def test_process_order_permanent_marks_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYMENT_FORCE_RESULT", "failure_permanent")
    order = {
        "orderId": "o1",
        "userId": "u1",
        "status": "PAYMENT_PENDING",
        "attemptCount": 0,
    }
    fake_repo = MagicMock()
    fake_repo.get_order.return_value = order

    event = {
        "Records": [
            {
                "body": json.dumps(
                    {"orderId": "o1", "userId": "u1", "totalAmount": 1.0, "createdAt": "t"}
                )
            }
        ]
    }

    with patch("handlers.process_order.OrdersRepository", return_value=fake_repo):
        process_order.handler(event, MagicMock())

    fake_repo.mark_payment_failed_permanent.assert_called_once()
