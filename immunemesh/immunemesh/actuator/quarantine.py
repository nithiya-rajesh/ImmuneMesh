"""
Agent-level quarantine.

This is coarser than an antibody match: an antibody blocks one piece of
KNOWN-BAD CONTENT, mesh-wide. Quarantine pauses one AGENT entirely, once
that agent itself has been confirmed compromised — every subsequent call
it receives is blocked regardless of content, until a human clears it.
See docs/architecture.md's "revoke scope" response actuator.
"""

from __future__ import annotations


class QuarantineManager:
    """Tracks which agents have been paused entirely, mesh-wide."""

    def __init__(self):
        self.quarantined_agents: set[str] = set()

    def is_quarantined(self, agent_id: str) -> bool:
        return agent_id in self.quarantined_agents

    def quarantine(self, agent_id: str, reason: str = "") -> None:
        self.quarantined_agents.add(agent_id)

    def clear(self, agent_id: str) -> None:
        """Manually clear an agent after human review."""
        self.quarantined_agents.discard(agent_id)
