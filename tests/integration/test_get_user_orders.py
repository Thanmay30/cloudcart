from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from handlers import get_user_orders


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORDERS_TABLE_NAME", "orders")
    monkeypatch.setenv("IDEMPOTENCY_TABLE_NAME", "idem")
    monkeypatch.setenv("ORDER_PROCESSING_QUEUE_URL", "https://sqs.example/queue")


def test_list_orders_forbidden_cross_user() -> None:
    fake_repo = MagicMock()
    event = {
        "headers": {"X-User-Id": "u1"},
        "pathParameters": {"userId": "u2"},
    }
    with patch("handlers.get_user_orders.OrdersRepository", return_value=fake_repo):
        resp = get_user_orders.handler(event, MagicMock())

    assert resp["statusCode"] == 403
    fake_repo.query_orders_by_user.assert_not_called()


def test_list_orders_success() -> None:
    fake_repo = MagicMock()
    fake_repo.query_orders_by_user.return_value = [
        {"orderId": "a", "userId": "u1", "createdAt": "2", "status": "PAID"},
        {"orderId": "b", "userId": "u1", "createdAt": "1", "status": "PAID"},
    ]
    event = {
        "headers": {"X-User-Id": "u1"},
        "pathParameters": {"userId": "u1"},
    }
    with patch("handlers.get_user_orders.OrdersRepository", return_value=fake_repo):
        resp = get_user_orders.handler(event, MagicMock())

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert len(body["data"]["orders"]) == 2
