"""Thin DynamoDB client helpers."""

from __future__ import annotations

from typing import Any, Callable

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.client import BaseClient

ClientFactory = Callable[[], Any]


def default_dynamodb_client() -> BaseClient:
    return boto3.client("dynamodb")


_ser = TypeSerializer()
_des = TypeDeserializer()


def to_ddb_item(obj: dict[str, Any]) -> dict[str, Any]:
    return {k: _ser.serialize(v) for k, v in obj.items()}


def from_ddb_item(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {k: _des.deserialize(v) for k, v in item.items()}
