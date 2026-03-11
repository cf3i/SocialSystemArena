"""Base adapter interface."""

from __future__ import annotations

from typing import Protocol

from ..core.types import AgentResult


class AgentAdapter(Protocol):
    def dispatch(
        self,
        runtime_id: str,
        message: str,
        timeout_sec: int = 300,
        retries: int = 1,
    ) -> AgentResult:
        ...
