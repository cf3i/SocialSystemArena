"""Mock adapter for local simulation and tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.types import AgentResult


@dataclass
class MockAdapter:
    scripted_decisions: dict[str, list[str]] = field(default_factory=dict)

    def dispatch(
        self,
        runtime_id: str,
        message: str,
        timeout_sec: int = 300,
        retries: int = 1,
    ) -> AgentResult:
        del timeout_sec, retries
        scripted = self.scripted_decisions.get(runtime_id, [])
        if scripted:
            decision = scripted.pop(0)
        else:
            # default deterministic behavior for dry run
            if "smalltalk" in message.lower():
                decision = "smalltalk"
            elif "reject" in message.lower():
                decision = "reject"
            elif "vote" in message.lower():
                decision = "yes"
            else:
                decision = "next"

        return AgentResult(
            decision=decision,
            summary=f"mock:{runtime_id}:{decision}",
            raw_output=message[:500],
            updates={"last_agent": runtime_id},
        )
