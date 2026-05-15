"""Order persistence and queries."""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Callable

from botocore.exceptions import ClientError

from shared.dynamodb import default_dynamodb_client, from_ddb_item, to_ddb_item
from shared.errors import AppError
from shared.idempotency import idempotency_item as build_idempotency_record
from shared.idempotency import idempotency_key_hash as hash_idempotency
ClientFactory = Callable[[], Any]


def _convert_numbers(obj: Any) -> Any:
    if isinstance(obj, list):
        return [_convert_numbers(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _convert_numbers(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


class OrdersRepository:
    def __init__(
        self,
        orders_table: str,
        idempotency_table: str,
        *,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._orders_table = orders_table
        self._idem_table = idempotency_table
        self._client_factory = client_factory or default_dynamodb_client

    @property
    def client(self) -> Any:
        return self._client_factory()

    def get_order_raw(self, order_id: str) -> dict[str, Any] | None:
        resp = self.client.get_item(
            TableName=self._orders_table,
            Key=to_ddb_item({"orderId": order_id}),
            ConsistentRead=True,
        )
        return from_ddb_item(resp.get("Item"))

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        raw = self.get_order_raw(order_id)
        return _convert_numbers(raw) if raw else None

    def query_orders_by_user(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        resp = self.client.query(
            TableName=self._orders_table,
            IndexName="userId-createdAt-index",
            KeyConditionExpression="userId = :u",
            ExpressionAttributeValues=to_ddb_item({":u": user_id}),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = [from_ddb_item(i) for i in resp.get("Items", [])]
        return [_convert_numbers(i) for i in items if i]

    def transact_create_order_and_idempotency(
        self,
        *,
        order: dict[str, Any],
        user_id: str,
        idempotency_key: str,
        created_at: str,
        expires_at: int,
    ) -> bool:
        """
        Returns True if a new order was created.
        Returns False if idempotency key already exists (transaction cancelled).
        """
        ikh = hash_idempotency(user_id, idempotency_key)
        idem = build_idempotency_record(
            idempotency_key_hash=ikh,
            user_id=user_id,
            idempotency_key=idempotency_key,
            order_id=order["orderId"],
            created_at=created_at,
            expires_at=expires_at,
        )
        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self._orders_table,
                            "Item": to_ddb_item(order),
                            "ConditionExpression": "attribute_not_exists(orderId)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._idem_table,
                            "Item": to_ddb_item(idem),
                            "ConditionExpression": "attribute_not_exists(idempotencyKeyHash)",
                        }
                    },
                ]
            )
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "TransactionCanceledException":
                return False
            raise

    def get_idempotency_record(self, user_id: str, idempotency_key: str) -> dict[str, Any] | None:
        ikh = hash_idempotency(user_id, idempotency_key)
        resp = self.client.get_item(
            TableName=self._idem_table,
            Key=to_ddb_item({"idempotencyKeyHash": ikh}),
            ConsistentRead=True,
        )
        raw = from_ddb_item(resp.get("Item"))
        return _convert_numbers(raw) if raw else None

    def update_order_status(
        self,
        order_id: str,
        *,
        status: str,
        updated_at: str,
        failure_reason: str | None = None,
        attempt_count: int | None = None,
        expected_current_status: str | None = None,
    ) -> None:
        names: dict[str, str] = {"#s": "status", "#u": "updatedAt"}
        values: dict[str, Any] = {":s": status, ":u": updated_at}
        expr = "SET #s = :s, #u = :u"
        if failure_reason is not None:
            names["#f"] = "failureReason"
            values[":f"] = failure_reason
            expr += ", #f = :f"
        if attempt_count is not None:
            names["#a"] = "attemptCount"
            values[":a"] = attempt_count
            expr += ", #a = :a"

        kwargs: dict[str, Any] = {
            "TableName": self._orders_table,
            "Key": to_ddb_item({"orderId": order_id}),
            "UpdateExpression": expr,
            "ExpressionAttributeNames": names,
            "ExpressionAttributeValues": to_ddb_item(values),
        }
        if expected_current_status:
            kwargs["ConditionExpression"] = "#s = :cur"
            values[":cur"] = expected_current_status

        try:
            self.client.update_item(**kwargs)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise AppError(
                    code="ORDER_STATE_CONFLICT",
                    message="Order status changed; retry the operation",
                    status_code=409,
                ) from exc
            raise

    def cancel_order(self, order_id: str, *, updated_at: str) -> None:
        names = {"#s": "status", "#u": "updatedAt"}
        values: dict[str, Any] = {
            ":cancelled": "CANCELLED",
            ":u": updated_at,
            ":p": "PAYMENT_PENDING",
            ":f": "FAILED",
        }
        self.client.update_item(
            TableName=self._orders_table,
            Key=to_ddb_item({"orderId": order_id}),
            UpdateExpression="SET #s = :cancelled, #u = :u",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=to_ddb_item(values),
            ConditionExpression="#s IN (:p, :f)",
        )

    def add_attempt_count(self, order_id: str, *, updated_at: str) -> None:
        self.client.update_item(
            TableName=self._orders_table,
            Key=to_ddb_item({"orderId": order_id}),
            UpdateExpression="ADD attemptCount :one SET updatedAt = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues=to_ddb_item(
                {":one": 1, ":u": updated_at, ":p": "PAYMENT_PENDING"}
            ),
            ConditionExpression="#s = :p",
        )

    def mark_payment_failed_permanent(
        self,
        order_id: str,
        *,
        updated_at: str,
        failure_reason: str,
        increment_attempt: bool = True,
    ) -> None:
        names = {"#s": "status", "#u": "updatedAt", "#f": "failureReason"}
        values: dict[str, Any] = {
            ":failed": "FAILED",
            ":u": updated_at,
            ":r": failure_reason,
            ":p": "PAYMENT_PENDING",
        }
        expr = "SET #s = :failed, #u = :u, #f = :r"
        if increment_attempt:
            expr += " ADD attemptCount :one"
            values[":one"] = 1
        self.client.update_item(
            TableName=self._orders_table,
            Key=to_ddb_item({"orderId": order_id}),
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=to_ddb_item(values),
            ConditionExpression="#s = :p",
        )

    def mark_payment_succeeded(self, order_id: str, *, updated_at: str) -> None:
        self.update_order_status(
            order_id,
            status="PAID",
            updated_at=updated_at,
            expected_current_status="PAYMENT_PENDING",
        )

    def try_cancel_order(self, order_id: str, *, updated_at: str) -> bool:
        """Returns True if updated to CANCELLED."""
        try:
            self.cancel_order(order_id, updated_at=updated_at)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
