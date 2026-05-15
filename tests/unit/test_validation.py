from __future__ import annotations

import pytest

from shared.errors import AppError
from shared.validation import parse_create_order_body, require_header, total_amount


def test_parse_create_order_valid() -> None:
    body = {
        "items": [
            {
                "productId": "p1",
                "name": "N",
                "quantity": 2,
                "unitPrice": 12.5,
            }
        ]
    }
    out = parse_create_order_body(body)
    assert len(out["items"]) == 1
    assert total_amount(out["items"]) == "25.00"


def test_require_header_missing() -> None:
    with pytest.raises(AppError) as exc:
        require_header(None, "X-User-Id")
    assert exc.value.status_code == 400


def test_parse_invalid_quantity() -> None:
    body = {
        "items": [
            {"productId": "p", "name": "n", "quantity": -1, "unitPrice": 1},
        ]
    }
    with pytest.raises(AppError) as exc:
        parse_create_order_body(body)
    assert exc.value.code == "INVALID_QUANTITY"
