# CloudCart — API Reference

Base URL: the `CloudCartHttpApiUrl` output from `cdk deploy` (API Gateway HTTP API).

All successful responses use:

```json
{ "success": true, "data": { ... } }
```

Errors use:

```json
{ "success": false, "error": { "code": "SOME_CODE", "message": "Human readable text" } }
```

## POST /orders

Creates an order and enqueues it for asynchronous payment simulation.

**Headers**

- `X-User-Id` (required)
- `Idempotency-Key` (required)

**Body**

```json
{
  "items": [
    {
      "productId": "prod_001",
      "name": "Wireless Mouse",
      "quantity": 2,
      "unitPrice": 24.99
    }
  ]
}
```

**Responses**

- `201` — new order created; `data.idempotentReplay` is `false`.
- `200` — duplicate idempotent request; `data.idempotentReplay` is `true` and `data` contains the original order.
- `400` — missing headers, invalid JSON, invalid items, non-positive quantity, or negative price.
- `500` — unexpected persistence or enqueue failures.

## GET /orders/{orderId}

**Headers**

- `X-User-Id` (required)

**Responses**

- `200` — order returned.
- `400` — missing header or path parameter.
- `403` — order belongs to another user.
- `404` — order not found.

## GET /orders/user/{userId}

Lists recent orders for a user using the `userId-createdAt-index` GSI.

**Headers**

- `X-User-Id` (required, must match `{userId}`)

**Responses**

- `200` — `{ "orders": [ ... ] }` sorted by `createdAt` descending (service-side query order).
- `403` — caller attempts to list another user’s orders.

## POST /orders/{orderId}/cancel

**Headers**

- `X-User-Id` (required)

**Responses**

- `200` — order moved to `CANCELLED` when previously `PAYMENT_PENDING` or `FAILED`.
- `403` — wrong user.
- `404` — order missing.
- `409` — invalid cancellation (for example `PAID` or `SHIPPED`).

## curl examples

Replace `API_URL`, `ORDER_ID`, and `USER_ID` with real values from your deployment output.

```bash
export API_URL="https://xxxxxxxx.execute-api.us-east-1.amazonaws.com"
export USER_ID="user_123"
export IDEM_KEY="$(uuidgen)"

curl -sS -X POST "$API_URL/orders" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -H "Idempotency-Key: $IDEM_KEY" \
  -d '{"items":[{"productId":"p1","name":"Notebook","quantity":1,"unitPrice":12.5}]}'

# Copy orderId from the JSON response into ORDER_ID for the following calls.
export ORDER_ID="paste-order-id-here"

curl -sS "$API_URL/orders/$ORDER_ID" -H "X-User-Id: $USER_ID"

curl -sS "$API_URL/orders/user/$USER_ID" -H "X-User-Id: $USER_ID"

curl -sS -X POST "$API_URL/orders/$ORDER_ID/cancel" -H "X-User-Id: $USER_ID"
```

## Authentication note

`X-User-Id` is a deliberate stand-in for a real identity provider. In production you would validate JWTs from Amazon Cognito, OIDC, or a corporate IdP and derive `userId` from verified claims rather than trusting a client-supplied header.
