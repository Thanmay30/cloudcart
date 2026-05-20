# CloudCart — Serverless Order Processing System on AWS

CloudCart is a serverless backend for order processing on AWS. Orders are accepted through API Gateway, persisted in DynamoDB, and processed asynchronously via SQS and Lambda. The system is built around idempotent APIs, structured logging, least-privilege IAM via CDK, and explicit failure handling with a dead-letter queue.

This is a portfolio and learning project. It is not running in production, and `X-User-Id` is a stand-in for a real identity system.

## My Role

Solo project. I designed the architecture, wrote all Lambda handlers, defined the CDK infrastructure stack, configured the SQS/DLQ workflow, and set up the CI pipeline and test suite.

## Why this project exists

Hands-on practice with AWS serverless architecture, fault-tolerant backend design, and operational clarity: duplicate-safe writes, queue-backed async processing, retries, DLQs, observability, and infrastructure as code.

## Text architecture diagram

```text
Client
  -> Amazon API Gateway (HTTP API)
  -> Lambda (Create / Get / List / Cancel)
  -> Amazon DynamoDB (orders + idempotency)
  -> Amazon SQS (OrderProcessingQueue)
  -> Lambda (ProcessOrder)
  -> Amazon DynamoDB (status updates)
  -> Amazon CloudWatch Logs
  -> Amazon SQS DLQ (failed messages after retries)
```

## AWS services used

- Amazon API Gateway — HTTP API for JSON routes
- AWS Lambda — Python 3.11 handlers
- Amazon DynamoDB — orders table with GSI, idempotency table with TTL
- Amazon SQS — primary processing queue
- Amazon SQS — dead-letter queue for poison / persistent failures
- Amazon CloudWatch Logs — JSON structured log lines
- AWS IAM — scoped function policies
- AWS CDK v2 — TypeScript infrastructure

## Key engineering concepts

- Idempotent APIs with server-side deduplication
- Event-driven, asynchronous processing
- Queue-based load leveling and retries
- Dead-letter queues for isolation and inspection
- Structured logging for operations-friendly search
- Least-privilege IAM via CDK grants
- Infrastructure as code
- Unit and integration-style tests without live AWS calls

## Repository layout

```text
cloudcart/
  README.md
  .gitignore
  .env.example
  package.json
  package-lock.json
  cdk.json
  tsconfig.json
  pytest.ini
  requirements-dev.txt
  .github/workflows/ci.yml
  infrastructure/
    bin/cloudcart.ts
    lib/cloudcart-stack.ts
    lib/constructs/
  src/
    handlers/
    shared/
  tests/
  docs/
```

## API documentation

See [docs/api.md](docs/api.md) for endpoints, headers, payloads, and curl snippets.

## Prerequisites

- **Node.js 20+** and **npm** for CDK
- **Python 3.11+** recommended (CI uses 3.11; handlers target the Lambda 3.11 runtime)
- An AWS account and IAM principal allowed to deploy CDK stacks

## Local setup

```bash
cd cloudcart
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
npm run build
npx cdk synth
```

## First-time CDK bootstrap

Run once per account and region combination:

```bash
npx cdk bootstrap aws://ACCOUNT_ID/REGION
```

## Deploy

```bash
npm run build
npx cdk deploy
```

Note the `CloudCartHttpApiUrl` output — that is the base URL for curl tests.

### Removal policy (cost and cleanup)

DynamoDB tables, queues, and CloudWatch log groups in this stack use `RemovalPolicy.DESTROY` so personal sandboxes clean up easily. **Do not enable `DESTROY` for production data stores.** Switch to `RETAIN` and add backups when moving beyond experiments.

## Calling the API with curl

See [docs/api.md](docs/api.md). Every request uses JSON and mock identity via `X-User-Id`.

## Testing

```bash
source .venv/bin/activate
pytest
```

Details: [docs/testing.md](docs/testing.md).

## Architecture deep dive

See [docs/architecture.md](docs/architecture.md) for idempotency, SQS retry behavior, and DynamoDB keys.

## Design decisions

- **API Gateway + Lambda** — minimal ops overhead, per-use billing, and a natural fit for JSON HTTP handlers.
- **DynamoDB** — fast key-value access patterns for orders and idempotency metadata; GSI supports `GET /orders/user/{userId}` without a relational engine.
- **SQS** — decouples order acceptance from payment simulation, smooths bursts, and provides built-in retry semantics.
- **DLQ** — after `maxReceiveCount` attempts, poison messages are quarantined for inspection instead of blocking the main queue indefinitely.
- **Mock `X-User-Id`** — keeps the project centered on distributed systems concerns; swap for Cognito or OIDC JWT validation in a production variant.
- **Idempotency** — network retries and double-clicks should never create two orders for the same logical request; conditional transactions make that story crisp in interviews.
- **Statuses** — `PROCESSING`, `SHIPPED`, and `DELIVERED` exist in the schema for a realistic order lifecycle story, but this codebase only automates payment outcomes (`PAYMENT_PENDING` → `PAID` or `FAILED`) plus `CANCELLED`.

## Environment variables

Lambdas receive table names, queue URLs, and tuning knobs from CDK. Local `.env` files are optional for experiments; copy `.env.example` if you want to run snippets locally.

| Variable | Purpose |
| --- | --- |
| `ORDERS_TABLE_NAME` | DynamoDB orders table |
| `IDEMPOTENCY_TABLE_NAME` | DynamoDB idempotency table |
| `ORDER_PROCESSING_QUEUE_URL` | SQS queue URL for async processing |
| `PAYMENT_FAILURE_RATE` | Baseline failure probability for the payment simulator (`0.0`–`1.0`) |
| `PAYMENT_FORCE_RESULT` | Optional test override: `success`, `failure_retry`, `failure_permanent` |

## GitHub Actions CI

CI installs Python dependencies, runs `pytest`, installs npm packages with `npm ci`, runs `npm run build`, and executes `npx cdk synth`. No automatic deploy is configured.

Treat the **`cloudcart/` directory as the Git repository root** so relative paths in CI match your workspace.

## Future improvements

- Amazon Cognito authorizer on API Gateway
- Inventory or catalog microservice with conditional stock checks
- AWS Step Functions for multi-step fulfillment orchestration
- Amazon CloudWatch metrics and alarms on DLQ depth and Lambda errors
- AWS X-Ray tracing
- Usage plans and throttling policies on API Gateway
- Real payment provider integration behind a bounded interface
