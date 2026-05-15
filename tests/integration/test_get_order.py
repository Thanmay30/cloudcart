from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from handlers import get_order


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORDERS_TABLE_NAME", "orders")
    monkeypatch.setenv("IDEMPOTENCY_TABLE_NAME", "idem")
    monkeypatch.setenv("ORDER_PROCESSING_QUEUE_URL", "https://sqs.example/queue")


def test_get_order_wrong_user() -> None:
    fake_repo = MagicMock()
    fake_repo.get_order.return_value = {
        "orderId": "o1",
        "userId": "u2",
        "status": "PAID",
        "items": [],
        "totalAmount": 1,
    }

    event = {
        "headers": {"X-User-Id": "u1"},
        "pathParameters": {"orderId": "o1"},
    }
    with patch("handlers.get_order.OrdersRepository", return_value=fake_repo):
        resp = get_order.handler(event, MagicMock())

    assert resp["statusCode"] == 403


def test_get_order_success() -> None:
    fake_repo = MagicMock()
    fake_repo.get_order.return_value = {
        "orderId": "o1",
        "userId": "u1",
        "status": "PAID",
        "items": [],
        "totalAmount": 1,
    }

    event = {
        "headers": {"X-User-Id": "u1"},
        "pathParameters": {"orderId": "o1"},
    }
    with patch("handlers.get_order.OrdersRepository", return_value=fake_repo):
        resp = get_order.handler(event, MagicMock())

    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["success"] is True
