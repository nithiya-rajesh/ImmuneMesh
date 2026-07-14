"""
Canary-token signal.

A random per-call token is silently appended to an agent's system prompt.
A legitimate agent has no reason to ever repeat that token back in its
output. If it does, that's near-certain evidence of prompt leakage or
injection — the agent is echoing its own internal context back out, which
is exactly the mechanism self-replicating prompt attacks rely on (see
docs/architecture.md, section 4).

Canary detection is treated as an absolute, non-adaptive signal everywhere
else in this codebase (see immunemesh/signals/baseline.py) — it is never
allowed to be "learned" as normal, unlike the mirroring score.
"""

from __future__ import annotations

import uuid

from langchain.messages import SystemMessage


def generate_canary() -> str:
    return f"CANARY-{uuid.uuid4().hex[:8]}"


def inject_into_system_message(system_message, canary: str):
    """Return a new SystemMessage with the canary token appended as a block."""
    existing_blocks = list(system_message.content_blocks) if system_message else []
    return SystemMessage(
        content=existing_blocks + [{"type": "text", "text": f"[session-token:{canary}]"}]
    )


def canary_leaked(canary: str, output_text: str) -> bool:
    return canary in output_text
