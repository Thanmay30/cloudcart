from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from handlers import create_order


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORDERS_TABLE_NAME", "orders")
    monkeypatch.setenv("IDEMPOTENCY_TABLE_NAME", "idem")
    monkeypatch.setenv("ORDER_PROCESSING_QUEUE_URL", "https://sqs.example/queue")


def _event(body: dict, headers: dict | None = None) -> dict:
    return {
        "version": "2.0",
        "headers": headers or {},
        "body": json.dumps(body),
    }


def test_create_order_success() -> None:
    headers = {"X-User-Id": "u1", "Idempotency-Key": "k1"}
    body = {
        "items": [
            {
                "productId": "p1",
                "name": "Item",
                "quantity": 2,
                "unitPrice": 10.0,
            }
        ]
    }
    fake_repo = MagicMock()
    fake_repo.transact_create_order_and_idempotency.return_value = True
    fake_repo.get_order.side_effect = lambda oid: {"orderId": oid, "status": "PAYMENT_PENDING"}

    with patch("handlers.create_order.OrdersRepository", return_value=fake_repo), patch(
        "handlers.create_order.send_order_processing_message"
    ) as send:
        resp = create_order.handler(_event(body, headers), MagicMock(aws_request_id="req-1"))

    assert resp["statusCode"] == 201
    payload = json.loads(resp["body"])
    assert payload["success"] is True
    assert payload["data"]["idempotentReplay"] is False
    send.assert_called_once()


def test_create_order_missing_user() -> None:
    resp = create_order.handler(
        _event({"items": [{"productId": "p", "name": "n", "quantity": 1, "unitPrice": 1}]}),
        MagicMock(),
    )
    assert resp["statusCode"] == 400


def test_create_order_missing_idempotency() -> None:
    resp = create_order.handler(
        _event(
            {"items": [{"productId": "p", "name": "n", "quantity": 1, "unitPrice": 1}]},
            {"X-User-Id": "u1"},
        ),
        MagicMock(),
    )
    assert resp["statusCode"] == 400


def test_create_order_invalid_quantity() -> None:
    resp = create_order.handler(
        _event(
            {
                "items": [
                    {"productId": "p", "name": "n", "quantity": 0, "unitPrice": 1},
                ]
            },
            {"X-User-Id": "u1", "Idempotency-Key": "k"},
        ),
        MagicMock(),
    )
    assert resp["statusCode"] == 400


def test_create_order_idempotent_replay() -> None:
    headers = {"X-User-Id": "u1", "Idempotency-Key": "k1"}
    body = {
        "items": [
            {"productId": "p1", "name": "Item", "quantity": 1, "unitPrice": 5},
        ]
    }
    existing = {
        "orderId": "o-existing",
        "userId": "u1",
        "status": "PAYMENT_PENDING",
        "items": [],
        "totalAmount": 5,
    }
    fake_repo = MagicMock()
    fake_repo.transact_create_order_and_idempotency.return_value = False
    fake_repo.get_idempotency_record.return_value = {"orderId": "o-existing"}
    fake_repo.get_order.return_value = existing

    with patch("handlers.create_order.OrdersRepository", return_value=fake_repo), patch(
        "handlers.create_order.send_order_processing_message"
    ) as send:
        resp = create_order.handler(_event(body, headers), MagicMock())

    assert resp["statusCode"] == 200
    payload = json.loads(resp["body"])
    assert payload["data"]["idempotentReplay"] is True
    send.assert_not_called()
