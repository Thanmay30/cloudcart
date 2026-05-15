"""Idempotency key hashing and helpers."""

from __future__ import annotations

import hashlib
import time
from typing import Any


def idempotency_key_hash(user_id: str, idempotency_key: str) -> str:
    raw = f"{user_id}:{idempotency_key}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def idempotency_ttl_epoch_seconds(ttl_days: int = 7) -> int:
    return int(time.time()) + ttl_days * 24 * 60 * 60


def idempotency_item(
    *,
    idempotency_key_hash: str,
    user_id: str,
    idempotency_key: str,
    order_id: str,
    created_at: str,
    expires_at: int,
) -> dict[str, Any]:
    return {
        "idempotencyKeyHash": idempotency_key_hash,
        "userId": user_id,
        "idempotencyKey": idempotency_key,
        "orderId": order_id,
        "createdAt": created_at,
        "expiresAt": expires_at,
    }
