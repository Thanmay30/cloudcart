"""SQS client and send helpers."""

from __future__ import annotations

import json
from typing import Any, Callable

import boto3
from botocore.client import BaseClient

ClientFactory = Callable[[], BaseClient]


def default_sqs_client() -> BaseClient:
    return boto3.client("sqs")


def send_order_processing_message(
    queue_url: str,
    payload: dict[str, Any],
    *,
    client_factory: ClientFactory | None = None,
) -> None:
    client = (client_factory or default_sqs_client)()
    client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
