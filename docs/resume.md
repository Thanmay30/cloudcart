# CloudCart — Resume and Interview Notes

## Suggested resume bullets

- Built a serverless order-processing backend using API Gateway, Lambda, DynamoDB, and SQS to process order events asynchronously across AWS services.
- Implemented idempotency-key handling with DynamoDB to prevent duplicate order creation during repeated client requests and network retries.
- Designed retry and dead-letter queue workflows for failed payment events, improving fault isolation, recovery behavior, and debugging visibility.
- Added structured CloudWatch logs for order creation, duplicate requests, payment success, payment failure, and queue-processing outcomes.
- Defined AWS infrastructure with CDK, including Lambda functions, IAM roles, DynamoDB tables, SQS queues, API routes, and deployment configuration.

## Thirty-second pitch

CloudCart is a portfolio backend that accepts idempotent order creation through API Gateway, persists orders in DynamoDB, and pushes work to SQS so payment simulation happens off the request thread. Duplicate `Idempotency-Key` values resolve to the original order through a conditional transaction. Failed asynchronous work retries a few times, then lands in a DLQ where it is easy to inspect without blocking the primary queue.

## Likely follow-up questions

- **Why a transaction for idempotency?** It ties the first-time insert of the order and the idempotency record together so two writers cannot both succeed.
- **Why SQS between create and payment?** It decouples latency, absorbs bursts, and gives you retry and DLQ semantics for free compared to doing all work inline.
- **Why mock `X-User-Id`?** It keeps the project focused on distributed systems mechanics. Production would validate a signed token from Cognito or another IdP.
- **What would you add next?** Cognito authorizers, inventory checks, Step Functions for multi-step fulfillment, metrics and alarms on DLQ depth, and X-Ray for end-to-end traces.
