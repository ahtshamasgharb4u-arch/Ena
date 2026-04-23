from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LlmUsage:
    total_tokens: int | None = None


@dataclass(frozen=True)
class LlmResponse:
    text: str
    usage: LlmUsage


class LlmClient(Protocol):
    def complete(self, *, system: str, user: str) -> LlmResponse: ...


class AgentError(Exception):
    pass

