from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from handlers import cancel_order


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORDERS_TABLE_NAME", "orders")
    monkeypatch.setenv("IDEMPOTENCY_TABLE_NAME", "idem")
    monkeypatch.setenv("ORDER_PROCESSING_QUEUE_URL", "https://sqs.example/queue")


def _event(order_id: str, headers: dict) -> dict:
    return {
        "version": "2.0",
        "headers": headers,
        "pathParameters": {"orderId": order_id},
    }


def test_cancel_pending_success() -> None:
    order = {
        "orderId": "o1",
        "userId": "u1",
        "status": "PAYMENT_PENDING",
        "items": [],
        "totalAmount": 1,
    }
    fake_repo = MagicMock()
    fake_repo.try_cancel_order.return_value = True
    fake_repo.get_order.side_effect = [
        order,
        {**order, "status": "CANCELLED", "updatedAt": "2020-01-01T00:00:00Z"},
    ]

    with patch("handlers.cancel_order.OrdersRepository", return_value=fake_repo):
        resp = cancel_order.handler(
            _event("o1", {"X-User-Id": "u1"}), MagicMock(aws_request_id="r1")
        )

    assert resp["statusCode"] == 200
    payload = json.loads(resp["body"])
    assert payload["data"]["status"] == "CANCELLED"


def test_cancel_paid_conflict() -> None:
    order = {"orderId": "o1", "userId": "u1", "status": "PAID", "items": [], "totalAmount": 1}
    fake_repo = MagicMock()
    fake_repo.get_order.return_value = order

    with patch("handlers.cancel_order.OrdersRepository", return_value=fake_repo):
        resp = cancel_order.handler(
            _event("o1", {"X-User-Id": "u1"}), MagicMock()
        )

    assert resp["statusCode"] == 409


def test_cancel_wrong_user() -> None:
    order = {"orderId": "o1", "userId": "u2", "status": "PAYMENT_PENDING", "items": []}
    fake_repo = MagicMock()
    fake_repo.get_order.return_value = order

    with patch("handlers.cancel_order.OrdersRepository", return_value=fake_repo):
        resp = cancel_order.handler(
            _event("o1", {"X-User-Id": "u1"}), MagicMock()
        )

    assert resp["statusCode"] == 403
