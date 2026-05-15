"""Environment-driven configuration for Lambda and local tests."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    orders_table_name: str
    idempotency_table_name: str
    order_processing_queue_url: str
    payment_failure_rate: float
    payment_force_result: str | None

    @classmethod
    def from_environ(cls) -> AppConfig:
        orders = os.environ.get("ORDERS_TABLE_NAME", "")
        idem = os.environ.get("IDEMPOTENCY_TABLE_NAME", "")
        queue = os.environ.get("ORDER_PROCESSING_QUEUE_URL", "")
        rate_raw = os.environ.get("PAYMENT_FAILURE_RATE", "0.2")
        try:
            rate = float(rate_raw)
        except ValueError:
            rate = 0.2
        rate = max(0.0, min(1.0, rate))
        force = os.environ.get("PAYMENT_FORCE_RESULT", "").strip() or None
        return cls(
            orders_table_name=orders,
            idempotency_table_name=idem,
            order_processing_queue_url=queue,
            payment_failure_rate=rate,
            payment_force_result=force,
        )


def require_config_for_api(cfg: AppConfig) -> list[str]:
    missing: list[str] = []
    if not cfg.orders_table_name:
        missing.append("ORDERS_TABLE_NAME")
    if not cfg.idempotency_table_name:
        missing.append("IDEMPOTENCY_TABLE_NAME")
    if not cfg.order_processing_queue_url:
        missing.append("ORDER_PROCESSING_QUEUE_URL")
    return missing
