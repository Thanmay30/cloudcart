"""Payment simulation for async order processing."""

from __future__ import annotations

import os
import random
from typing import Literal

PaymentOutcome = Literal["success", "retryable_failure", "permanent_failure"]


def simulate_payment(
    *,
    order_id: str,
    attempt_count: int,
    payment_failure_rate: float,
    payment_force_result: str | None,
) -> PaymentOutcome:
    """
    Tests should set PAYMENT_FORCE_RESULT to:
    - success
    - failure_retry (SQS retry)
    - failure_permanent (mark FAILED)
    """
    force = (payment_force_result or os.environ.get("PAYMENT_FORCE_RESULT") or "").strip()
    if force == "success":
        return "success"
    if force == "failure_retry":
        return "retryable_failure"
    if force == "failure_permanent":
        return "permanent_failure"

    if random.random() >= payment_failure_rate:
        return "success"

    # Bias toward clearing the queue after repeated receives
    if attempt_count >= 2:
        return "permanent_failure"
    return "retryable_failure" if random.random() < 0.7 else "permanent_failure"
