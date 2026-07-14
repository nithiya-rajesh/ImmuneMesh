# ImmuneMesh — Architecture v2

**Positioning:** A runtime behavioral guardrail for multi-agent AI systems, delivered as LangGraph middleware. It does not try to make agents smarter or safer at the model level — it watches what agents *do* to each other's messages at runtime, and gives the mesh a shared memory so that once one agent is fooled, the rest aren't.

**One-line differentiator:** Every existing guardrail framework evaluates one message in isolation. ImmuneMesh is the only layer that watches the whole mesh over time and remembers.

---

## 1. Why this exists — the actual gap

Guardrail middleware for agent frameworks already exists and is maturing fast — LangChain ships native guardrails, and NeMo Guardrails / Guardrails AI are established third-party options. Big labs and platform vendors are investing heavily in defense-in-depth:

- **Input filtering / prompt shielding** — stripping known malicious patterns before they reach the model
- **Output moderation** — a secondary classifier checking a single response for PII or jailbreak content
- **Tool/API sandboxing** — limited-permission tokens so a compromised agent can't do unlimited damage
- **Audit logging** — recording prompts and responses for after-the-fact reconstruction

All four of these evaluate **one agent, one message, at one point in time.** None of them ask: *is this same payload echoing across three different agents in my mesh right now?* That question — propagation across the mesh, not content within a single message — is the actual blind spot, and it's exactly the mechanism that self-replicating prompt attacks (the Morris-II class) exploit. ImmuneMesh is built specifically to close that one gap, not to replace the other four layers. It's designed to sit alongside them as one more layer in a defense-in-depth stack, not instead of them.

**Why big tech hasn't built this themselves, most likely:** their guardrail investment is concentrated at the model level (training models to refuse replication) and at the single-message level (classifiers per call), partly because per-message classifiers are simpler to reason about and add less latency than a system that has to track state across an entire mesh over time. A mesh-wide behavioral memory is architecturally a different kind of system — closer to a distributed systems problem than a classifier problem — which is likely why it hasn't shown up as a first-party product yet.

---

## 2. Threat model

**Primary target:** self-replicating prompt propagation (Morris-II class) — an adversarial input tricks Agent A into mirroring that input into its own output; any downstream agent that consumes A's output re-triggers the same behavior, and the payload spreads without needing to exploit any traditional software vulnerability.

**Secondary target:** agent goal hijack and plan drift — an agent's actions diverge from what its system prompt and original task actually authorized, whether from injection, tool poisoning, or accumulated context corruption over a long session. This is a broader category than pure replication, and the same behavioral-monitoring infrastructure can catch both.

---

## 3. Core architecture

```
┌───────────────────────────────────────────────────────────────┐
│                    LangGraph application                       │
│                                                                  │
│   ┌──────────┐  before_model   ┌──────────┐  before_tool        │
│   │  Node A  │ ───────────────▶│ ImmuneMesh│───────────────▶   │
│   │ (agent)  │                 │ middleware│                    │
│   └────┬─────┘  after_model    └────┬──────┘  after_tool        │
│        │       ◀────────────────────┘                          │
│        ▼                                                        │
│   ┌──────────┐                                                 │
│   │  Node B  │  (same middleware attached identically)          │
│   └──────────┘                                                 │
└───────────────────────┬───────────────────────────────────────┘
                         │  signals + antibody sync
                         ▼
        ┌───────────────────────────────────────┐
        │        ImmuneMesh Control Plane         │
        │  (runs alongside the app, not per-node) │
        │                                         │
        │  ┌─────────────────────────────────┐    │
        │  │ Signal Extraction                │    │
        │  │ mirroring score · canary echo ·  │    │
        │  │ baseline drift · propagation graph│    │
        │  └───────────────┬───────────────────┘    │
        │                  ▼                        │
        │  ┌─────────────────────────────────┐    │
        │  │ Antibody Store ("lymph node")     │    │
        │  │ shared signatures, TTL, confidence│    │
        │  └───────────────┬───────────────────┘    │
        │                  ▼                        │
        │  ┌─────────────────────────────────┐    │
        │  │ Response Actuator                 │    │
        │  │ quarantine · revoke scope · alert │    │
        │  │ · structured audit log            │    │
        │  └─────────────────────────────────┘    │
        └───────────────────────────────────────┘
```

### Why this split (middleware in-process, control plane out-of-process)

The **middleware** is thin and lives inside the LangGraph process — it's just hook functions at `before_model`, `after_model`, `before_tool`, `after_tool`. It does not do any heavy computation itself; it forwards signals to the control plane and enforces whatever verdict comes back (allow, flag, block).

The **control plane** runs as a separate lightweight service (even just a local process for the MVP). It holds the antibody store and does the actual scoring. Splitting it this way means:
- The expensive part (embeddings, cross-agent correlation) doesn't add latency to every single node's hot path unless a decision is actually needed
- Multiple LangGraph apps / multiple agent meshes in an organization can share one control plane, which is what makes the "gossip across the whole mesh" idea actually work at any scale beyond a single demo

---

## 4. Detection layer — "behavioral attestation" signals

This is the part that actually answers "how is this agent behaving," not "what does this one message contain":

| Signal | What it measures | Catches |
|---|---|---|
| Mirroring score | Cosine similarity between an agent's input and its own output embeddings | Morris-II style replication |
| Canary echo | A random per-session token embedded in the system prompt; flagged if it reappears in output | Prompt leakage / injection confirmation |
| Propagation graph | Near-duplicate content hash appearing across 3+ agents within a short time window | Confirms worm-style spread vs. isolated incident |
| Baseline drift | Z-score deviation from an agent's normal tool-call rate, message length, and destination diversity | Plan drift / goal hijack, even without a text match to anything seen before |

None of these alone is reliable — mirroring score false-positives on legitimate summarization, baseline drift false-positives on genuinely varied workloads. The combination, correlated across the propagation graph, is what makes a verdict trustworthy. This is the actual research contribution, and the honest unsolved problem — see section 8.

---

## 5. Data model

**Immune Signal event**
```json
{
  "signal_id": "uuid",
  "timestamp": "iso8601",
  "agent_id": "string",
  "node_name": "string",
  "message_id": "uuid",
  "hook_point": "before_model | after_model | before_tool | after_tool",
  "mirroring_score": 0.0,
  "canary_echo_detected": false,
  "content_hash": "simhash",
  "baseline_zscore": 0.0,
  "verdict": "clean | suspicious | confirmed_malicious",
  "propagation_path": ["agent_a", "agent_b"]
}
```

**Antibody record**
```json
{
  "antibody_id": "uuid",
  "pattern_embedding_centroid": [0.0],
  "matched_phrase_patterns": ["string"],
  "confidence": 0.0,
  "first_seen_agent": "string",
  "confirmed_by": "innate | human_review",
  "ttl": "duration",
  "propagated_to": ["agent_list"]
}
```

**Behavioral baseline** (per agent, per node)
```json
{
  "agent_id": "string",
  "avg_message_length": 0.0,
  "avg_tool_calls_per_turn": 0.0,
  "typical_destinations": ["agent_list"],
  "window": "rolling_24h"
}
```

---

## 6. LangGraph integration specifics

LangGraph exposes explicit interception points before and after every model call and every tool call — this is the actual attach point, not a workaround:

- `before_model` — capture the input about to be sent; check canary tokens, compute input embedding
- `after_model` — capture the output; compute mirroring score against the input embedding; check for canary echo
- `before_tool` — check the antibody store for a match before allowing a tool call to fire
- `after_tool` — log the tool result, update the agent's rolling baseline

The middleware package should expose a single entry point that a developer adds once — the goal (per the LangGraph adoption strategy) is `pip install immunemesh` then a two-line attach to an existing graph, not a rebuild of their agent system.

---

## 7. Deployment topology options

- **Development/demo:** everything in one process — middleware and control plane both local, in-memory antibody store. This is the MVP scope (section 9).
- **Small production deployment:** control plane as a separate local service (FastAPI + Redis for the antibody store), middleware still per-app.
- **Enterprise/multi-team:** control plane as a shared internal service across multiple LangGraph applications/teams, so an antibody discovered by one team's mesh protects every other team's mesh immediately — this is the point where the "immune system" framing earns its name at real scale.

---

## 8. Honest, unsolved research problem

Distinguishing malicious mirroring from legitimate summarization/citation/translation is not solved by any single signal here. A production-credible version of this needs a benign corpus (summarization tasks, RAG citation tasks, translation tasks) to tune false-positive rates before any accuracy claim is made public. State this explicitly in any demo or writeup — it's a strength of the research framing, not a weakness, and it's what separates this from a vendor pitch.

---

## 9. MVP scope

- A LangGraph app with 4-6 simulated nodes (email assistant, summarizer, scheduler, research agent, notifier)
- ImmuneMesh middleware attached via `before_model`/`after_model`/`before_tool`/`after_tool` hooks
- Control plane as a single local process (in-memory antibody store is fine for MVP — Redis only needed once you want persistence across restarts)
- Local open-source LLM (via Ollama) for all agents — no dependency on a commercial API, and no terms-of-service exposure from running adversarial test payloads
- `sentence-transformers` for embeddings, run locally
- Minimal FastAPI + graph-visualization dashboard showing the mesh, colored by verdict, live during a demo run

---

## 10. Demo script

1. **Baseline run (no ImmuneMesh attached):** feed a Morris-II-style payload into the email-assistant node. Show it mirror into its own output, and show the summarizer node ingest and re-propagate it. Dashboard shows an unchecked red trail across the mesh.
2. **Attach ImmuneMesh, replay the same attack:** show the mirroring score spike at the first node's `after_model` hook. Show the antibody get written and synced to the control plane. Show the second node's `before_tool` (or `before_model`) hook catch the near-duplicate match and quarantine before it propagates further.
3. **Show the audit log** — the actual Immune Signal event trail, not just a red/green dashboard light.
4. **State the false-positive limitation out loud**, and show one deliberately benign summarization task passing cleanly through the same pipeline, to demonstrate you've thought about it rather than ignored it.

---

## 11. Differentiation summary (for pitch / README framing)

| Layer | What it checks | Who already does this |
|---|---|---|
| Input filtering | Known bad patterns in one message | LangChain guardrails, NeMo Guardrails |
| Output moderation | PII/jailbreak in one response | LangChain guardrails, Azure AI Content Safety-style classifiers |
| Tool sandboxing | Blast radius if an agent is compromised | Least-privilege token scoping (architecture practice, not a product gap) |
| Audit logging | Reconstruction after the fact | LangSmith, Langfuse |
| **Cross-agent propagation memory** | **Is this same payload spreading across the mesh right now, and has any agent already learned to recognize it** | **Nobody, as of mid-2026 — this is the wedge** |

---

## 12. Suggested repo structure

```
immunemesh/
├── middleware/         # langgraph_hooks.py — before_model/after_model/before_tool/after_tool
├── signals/            # mirroring_score.py, canary.py, baseline.py, propagation_graph.py
├── control_plane/       # antibody_store.py, gossip.py, api.py (FastAPI)
├── actuator/            # quarantine.py, audit_log.py
├── demo/                # simulated_mesh.py (LangGraph app), attack_payloads/, dashboard/
├── benchmarks/          # benign_corpus/, false_positive_eval.py
└── docs/
    └── architecture.md    # this file
```

---

*Next concrete step: stand up a minimal LangGraph app with 2 nodes and get the `before_model`/`after_model` hooks firing with just a print statement — before adding any real detection logic. Confirm the attach point works before building anything on top of it.*
