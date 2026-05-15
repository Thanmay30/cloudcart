from shared.idempotency import idempotency_key_hash


def test_idempotency_hash_stable() -> None:
    h1 = idempotency_key_hash("user_1", "abc")
    h2 = idempotency_key_hash("user_1", "abc")
    h3 = idempotency_key_hash("user_2", "abc")
    assert h1 == h2
    assert h1 != h3
