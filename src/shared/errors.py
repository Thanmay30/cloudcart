"""Domain and HTTP-oriented error codes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message}"
