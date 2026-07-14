"""
The antibody store — the "lymph node" from docs/architecture.md.

Once any agent confirms a threat, every other agent checks new input
against this shared memory FIRST, before even calling its model. A match
means instant quarantine of that message — no LLM call happens at all,
so the attack never gets a chance to execute against that agent.

This is the mechanic that earns the "immune system" name: the first
exposure still causes some symptoms, but every subsequent exposure across
the mesh gets caught before the infection can take hold.

In this MVP, the store is shared by reference across every agent's
middleware in a single process. In a real multi-process / multi-team
deployment this would be a small networked service instead (see
docs/architecture.md, section 7 — "Deployment topology options") —
the matching logic here is identical either way.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import numpy as np

from immunemesh.signals.embeddings import cosine_similarity

ANTIBODY_MATCH_THRESHOLD = 0.85  # how similar new input must be to a known bad pattern


@dataclass
class Antibody:
    antibody_id: str
    embedding: np.ndarray
    confirmed_by_agent: str
    reason: str


@dataclass
class AntibodyStore:
    antibodies: list = field(default_factory=list)

    def check(self, embedding: np.ndarray):
        """Return (antibody, score) for the best match above threshold, else (None, 0.0)."""
        for antibody in self.antibodies:
            score = cosine_similarity(embedding, antibody.embedding)
            if score >= ANTIBODY_MATCH_THRESHOLD:
                return antibody, score
        return None, 0.0

    def add(self, embedding: np.ndarray, confirmed_by_agent: str, reason: str) -> Antibody:
        antibody = Antibody(
            antibody_id=f"AB-{uuid.uuid4().hex[:8]}",
            embedding=embedding,
            confirmed_by_agent=confirmed_by_agent,
            reason=reason,
        )
        self.antibodies.append(antibody)
        return antibody
