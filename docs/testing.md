# CloudCart — Testing

## Goals

- Keep `pytest` fast and runnable on a laptop without AWS credentials.
- Prefer small unit tests around validation, idempotency hashing, payment simulation, and response envelopes.
- Use integration-style tests for Lambda handlers with `unittest.mock` to stub `OrdersRepository` and SQS calls.

## Layout

- `tests/unit/` — pure helpers and deterministic branches (`validation`, `idempotency`, `payment`, `responses`).
- `tests/integration/` — handler tests that patch AWS-facing collaborators.

## Running tests locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

`pytest.ini` sets `pythonpath = src` so imports such as `handlers.create_order` resolve the same way as in Lambda.

## Continuous integration

GitHub Actions (`.github/workflows/ci.yml`) installs `requirements-dev.txt`, runs `pytest`, installs npm dependencies with `npm ci`, compiles TypeScript, and runs `npx cdk synth`. No deploy step is included.

## Mocking strategy

- **DynamoDB and SQS** — handler tests patch repositories and `send_order_processing_message` rather than calling real AWS APIs.
- **moto** — listed in `requirements-dev.txt` for optional experiments, but the default suite avoids heavy moto setup to keep CI predictable.

## Environment variables in tests

Handler tests set the following through `pytest` fixtures:

- `ORDERS_TABLE_NAME`
- `IDEMPOTENCY_TABLE_NAME`
- `ORDER_PROCESSING_QUEUE_URL`

Process-order tests additionally toggle `PAYMENT_FORCE_RESULT` to exercise success, retryable failure, and permanent failure branches.
