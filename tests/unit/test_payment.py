from __future__ import annotations

import pytest

from shared.payment import simulate_payment


def test_payment_force_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYMENT_FORCE_RESULT", "success")
    assert (
        simulate_payment(
            order_id="x",
            attempt_count=0,
            payment_failure_rate=1.0,
            payment_force_result=None,
        )
        == "success"
    )


def test_payment_force_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYMENT_FORCE_RESULT", "failure_retry")
    assert (
        simulate_payment(
            order_id="x",
            attempt_count=0,
            payment_failure_rate=0.0,
            payment_force_result=None,
        )
        == "retryable_failure"
    )


def test_payment_force_permanent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYMENT_FORCE_RESULT", "failure_permanent")
    assert (
        simulate_payment(
            order_id="x",
            attempt_count=0,
            payment_failure_rate=0.0,
            payment_force_result=None,
        )
        == "permanent_failure"
    )
