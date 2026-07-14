"""
Mirroring-score evaluation: per-agent adaptive baseline.

This is the corrected detection logic and the ONLY mirroring evaluation
path used anywhere in this codebase — there is no separate "flat global
threshold" version shipped alongside it. The earlier flat-threshold
design is documented in CHANGELOG.md as a fixed, known bug, not kept as
a live code path.

Why a flat global threshold doesn't work (found during the benign-corpus
run, see benchmarks/benign_corpus_eval.py): a single mirroring threshold
(0.75) flagged legitimate proofreading (0.902) and instruction-confirmation
(0.920) tasks as attacks, while the one confirmed real attack recorded in
this project's audit log scored lower (0.549 — see
logs/example_audit_log.jsonl).
One number cannot separate these — different agents legitimately have
different "normal" amounts of mirroring (a proofreading agent mirrors
most of its input by design; a research agent does not).

Fix: each agent keeps a rolling history of its own past confirmed-clean
mirroring scores. Once it has enough history, new scores are judged
against that agent's own mean/spread (a z-score) instead of one global
number. A brand-new agent with no history yet falls back to the global
threshold, but only in an ADVISORY capacity — see `evaluate()`.

Bootstrap deadlock, found and fixed: the first version of this gated
"is this score safe to learn from" on the same global threshold it was
trying to replace. An agent whose true normal sits above that threshold
could never accumulate enough history to graduate out of cold start —
it would deadlock, permanently advisory, forever. The fix decouples
*learning* (gated only by canary detection, which is always safe to
gate on) from *blocking* (gated by a warmed-up, agent-specific baseline).
See `should_record()`.

Canary-echo detection is never subject to this baseline — it fires
regardless of any agent's learned history, on purpose (see canary.py).
A baseline can legitimately learn that "this agent mirrors 90% of its
input" over time. It must never be able to learn "this agent leaking
its system prompt is normal."

Known, deliberate limitation (not solved here): because the baseline
learns from an agent's own recent history, a patient attacker could try
to gradually shift what "normal" looks like for an agent before
striking. This is mitigated slightly (bounded history so old data ages
out; canary is never adaptive) but the general problem of detecting slow,
deliberate baseline drift is unsolved future work — see docs/architecture.md
section 8 and README.md "Known limitations."
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

GLOBAL_FALLBACK_THRESHOLD = 0.75  # used only during an agent's cold start, advisory only
MIN_SAMPLES_FOR_BASELINE = 5
Z_SCORE_THRESHOLD = 2.5
MAX_HISTORY = 50  # bounds memory and lets old data age out


@dataclass
class AgentBaseline:
    """Tracks one agent's own normal range of mirroring scores over time."""

    agent_id: str
    history: list = field(default_factory=list)

    def evaluate(self, score: float) -> tuple[bool, str, str]:
        """
        Returns (flagged, mode, detail).

        During cold start, `flagged` is ADVISORY ONLY — it does not block
        the message and does not prevent the score from being learned.
        Only a flag from a warmed-up, per-agent baseline (i.e. a real
        deviation from this agent's own established normal) blocks.
        """
        if len(self.history) < MIN_SAMPLES_FOR_BASELINE:
            flagged = score >= GLOBAL_FALLBACK_THRESHOLD
            detail = f"cold start, {len(self.history)}/{MIN_SAMPLES_FOR_BASELINE} samples so far (advisory only)"
            return flagged, "global_fallback", detail

        mean = statistics.mean(self.history)
        stdev = statistics.pstdev(self.history) or 0.01  # floor to avoid divide-by-zero
        z = (score - mean) / stdev
        flagged = abs(z) >= Z_SCORE_THRESHOLD
        detail = f"z={z:.2f} (this agent's normal: mean={mean:.3f}, stdev={stdev:.3f})"
        return flagged, "per_agent_baseline", detail

    def should_record(self, mode: str, flagged: bool, canary_leaked: bool) -> bool:
        """
        Decides whether a score is safe to add to this agent's history.

        Canary leak is the only hard gate. During cold start we always
        record (absent a canary leak) so the agent can graduate out of
        cold start at all. Once warmed up, we stop recording a score the
        agent's own baseline just flagged, to avoid a confirmed outlier
        corrupting its future normal.
        """
        if canary_leaked:
            return False
        if mode == "global_fallback":
            return True
        return not flagged

    def record_clean(self, score: float) -> None:
        self.history.append(score)
        if len(self.history) > MAX_HISTORY:
            self.history.pop(0)
