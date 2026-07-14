"""
ImmuneMeshMiddleware — the single, final middleware attach point.

This consolidates every detection/response layer from the project's
build history (see CHANGELOG.md) into one `wrap_model_call` hook, in the
order they actually run:

  1. Agent-level quarantine check   (immunemesh.actuator.quarantine)
  2. Antibody store check           (immunemesh.control_plane.antibody_store)
  3. Canary-token injection + check (immunemesh.signals.canary)
  4. Mirroring score                (immunemesh.signals.embeddings)
  5. Per-agent adaptive baseline    (immunemesh.signals.baseline)
  6. Antibody + quarantine write-back on a confirmed threat
  7. Structured audit log entry     (immunemesh.actuator.audit_log)

There is no separate "flat global threshold" code path shipped alongside
this — the per-agent baseline (step 5) is the only mirroring evaluation
used in production here. See immunemesh/signals/baseline.py for why, and
CHANGELOG.md for the bug that an earlier flat-threshold version had.

Canary detection is absolute and bypasses the baseline entirely — see
immunemesh/signals/canary.py.
"""

from __future__ import annotations

from typing import Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import AIMessage

from immunemesh.actuator.audit_log import AuditLog
from immunemesh.actuator.quarantine import QuarantineManager
from immunemesh.control_plane.antibody_store import AntibodyStore
from immunemesh.signals.baseline import AgentBaseline
from immunemesh.signals.canary import canary_leaked, generate_canary, inject_into_system_message
from immunemesh.signals.embeddings import cosine_similarity, embed


class ImmuneMeshMiddleware(AgentMiddleware):
    """Attach one instance of this per LangGraph node/agent.

    All instances that should share threat intelligence must be given the
    SAME AntibodyStore, QuarantineManager, and AuditLog instances — that
    shared state is what makes this a mesh-wide immune system instead of
    N independent detectors. Each agent keeps its OWN AgentBaseline,
    since "normal" mirroring behavior is agent-specific by design.
    """

    def __init__(
        self,
        agent_id: str,
        antibody_store: AntibodyStore,
        quarantine: QuarantineManager,
        audit_log: AuditLog,
        baseline: AgentBaseline | None = None,
        on_event: Callable[[str, dict], None] | None = None,
    ):
        super().__init__()
        self.agent_id = agent_id
        self.store = antibody_store
        self.quarantine = quarantine
        self.audit_log = audit_log
        self.baseline = baseline or AgentBaseline(agent_id=agent_id)
        # Optional hook so callers (e.g. the live dashboard) can react to
        # events as they happen instead of only reading the audit log after.
        self.on_event = on_event or (lambda event_type, fields: None)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        input_text = request.messages[-1].content if request.messages else ""
        self.on_event("processing", {"agent_id": self.agent_id, "input_text": input_text})

        # --- 1. Is this agent itself already quarantined? (agent-level, content-agnostic) ---
        if self.quarantine.is_quarantined(self.agent_id):
            self.audit_log.log(
                agent_id=self.agent_id,
                hook_point="wrap_model_call",
                verdict="blocked_agent_quarantined",
                input_text=input_text,
            )
            self.on_event("blocked", {"agent_id": self.agent_id, "reason": "agent_quarantined", "input_text": input_text})
            return ModelResponse(result=[AIMessage(content="[BLOCKED BY IMMUNEMESH — agent is quarantined]")])

        input_embedding = embed(input_text)

        # --- 2. Does this specific content match a known antibody? (mesh-wide, content-level) ---
        matched_antibody, match_score = self.store.check(input_embedding)
        if matched_antibody:
            self.audit_log.log(
                agent_id=self.agent_id,
                hook_point="wrap_model_call",
                verdict="blocked_antibody_match",
                matched_antibody_id=matched_antibody.antibody_id,
                match_score=round(match_score, 3),
                input_text=input_text,
            )
            self.on_event("blocked", {
                "agent_id": self.agent_id, "reason": "antibody_match",
                "antibody_id": matched_antibody.antibody_id, "match_score": round(match_score, 3),
                "source_agent": matched_antibody.confirmed_by_agent, "input_text": input_text,
            })
            return ModelResponse(result=[AIMessage(content="[BLOCKED BY IMMUNEMESH — known threat pattern]")])

        # --- 3. No prior knowledge — inject a canary and call the model ---
        canary = generate_canary()
        new_request = request.override(
            system_message=inject_into_system_message(request.system_message, canary)
        )
        response = handler(new_request)
        output_text = response.result[-1].content

        # --- 4/5. Mirroring score, evaluated against this agent's own baseline ---
        output_embedding = embed(output_text)
        mirroring_score = cosine_similarity(input_embedding, output_embedding)
        leaked = canary_leaked(canary, output_text)
        baseline_flagged, mode, detail = self.baseline.evaluate(mirroring_score)

        reasons = []
        if leaked:
            reasons.append("canary_echo_detected")
        # Cold-start baseline flags are advisory only (see signals/baseline.py) —
        # only a flag from a WARMED-UP, per-agent baseline actually blocks.
        if baseline_flagged and mode == "per_agent_baseline":
            reasons.append(f"baseline_deviation ({detail})")

        if self.baseline.should_record(mode, baseline_flagged, leaked):
            self.baseline.record_clean(mirroring_score)

        # --- 6. Write back to shared mesh memory on a confirmed threat ---
        if reasons:
            verdict = "confirmed_malicious"
            antibody = self.store.add(input_embedding, confirmed_by_agent=self.agent_id, reason=", ".join(reasons))
            self.quarantine.quarantine(self.agent_id, reason=", ".join(reasons))
            self.on_event("confirmed_malicious", {
                "agent_id": self.agent_id, "reasons": reasons, "antibody_id": antibody.antibody_id,
                "mirroring_score": round(mirroring_score, 3), "canary_leaked": leaked,
                "input_text": input_text, "output_text": output_text,
            })
        else:
            verdict = "clean"
            self.on_event("clean", {
                "agent_id": self.agent_id, "mirroring_score": round(mirroring_score, 3),
                "canary_leaked": leaked, "input_text": input_text, "output_text": output_text,
            })

        # --- 7. Structured audit trail regardless of verdict ---
        self.audit_log.log(
            agent_id=self.agent_id,
            hook_point="wrap_model_call",
            mirroring_score=round(mirroring_score, 3),
            canary_echo_detected=leaked,
            baseline_mode=mode,
            baseline_detail=detail,
            verdict=verdict,
            input_text=input_text,
            output_text=output_text,
        )

        return response
