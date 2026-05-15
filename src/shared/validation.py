"""Request validation for orders API."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from shared.errors import AppError


def require_header(headers: dict[str, str] | None, name: str) -> str:
    if not headers:
        raise AppError(
            code="MISSING_HEADER",
            message=f"Missing required header: {name}",
            status_code=400,
        )
    # API Gateway can send mixed-case; normalize
    lower = {k.lower(): v for k, v in headers.items()}
    value = lower.get(name.lower())
    if value is None or str(value).strip() == "":
        raise AppError(
            code="MISSING_HEADER",
            message=f"Missing required header: {name}",
            status_code=400,
        )
    return str(value).strip()


def parse_create_order_body(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise AppError(
            code="INVALID_BODY",
            message="Request body must be a JSON object",
            status_code=400,
        )
    items = body.get("items")
    if not isinstance(items, list) or len(items) == 0:
        raise AppError(
            code="INVALID_ITEMS",
            message="items must be a non-empty array",
            status_code=400,
        )
    normalized: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            raise AppError(
                code="INVALID_ITEM",
                message="Each item must be an object",
                status_code=400,
            )
        product_id = raw.get("productId")
        name = raw.get("name")
        quantity = raw.get("quantity")
        unit_price = raw.get("unitPrice")
        if not isinstance(product_id, str) or not product_id.strip():
            raise AppError(
                code="INVALID_ITEM",
                message="productId must be a non-empty string",
                status_code=400,
            )
        if not isinstance(name, str) or not name.strip():
            raise AppError(
                code="INVALID_ITEM",
                message="name must be a non-empty string",
                status_code=400,
            )
        if isinstance(quantity, bool):
            raise AppError(
                code="INVALID_QUANTITY",
                message="quantity must be a positive integer",
                status_code=400,
            )
        if not isinstance(quantity, int):
            raise AppError(
                code="INVALID_QUANTITY",
                message="quantity must be a positive integer",
                status_code=400,
            )
        if quantity <= 0:
            raise AppError(
                code="INVALID_QUANTITY",
                message="quantity must be a positive integer",
                status_code=400,
            )
        if isinstance(unit_price, bool) or unit_price is None:
            raise AppError(
                code="INVALID_PRICE",
                message="unitPrice must be a number",
                status_code=400,
            )
        if not isinstance(unit_price, (int, float, str, Decimal)):
            raise AppError(
                code="INVALID_PRICE",
                message="unitPrice must be a number",
                status_code=400,
            )
        try:
            price_dec = Decimal(str(unit_price))
        except Exception as exc:  # noqa: BLE001 — validation path
            raise AppError(
                code="INVALID_PRICE",
                message="unitPrice must be a number",
                status_code=400,
            ) from exc
        if price_dec < 0:
            raise AppError(
                code="INVALID_PRICE",
                message="unitPrice must be >= 0",
                status_code=400,
            )
        normalized.append(
            {
                "productId": product_id.strip(),
                "name": name.strip(),
                "quantity": quantity,
                "unitPrice": str(price_dec.quantize(Decimal("0.01"))),
            }
        )
    return {"items": normalized}


def total_amount(items: list[dict[str, Any]]) -> str:
    total = Decimal("0")
    for it in items:
        q = Decimal(int(it["quantity"]))
        p = Decimal(str(it["unitPrice"]))
        total += q * p
    return str(total.quantize(Decimal("0.01")))
