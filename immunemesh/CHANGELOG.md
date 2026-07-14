# Changelog

This documents how ImmuneMesh was actually built, in order, since that
history wasn't captured cleanly at the time. Each entry below corresponds
to what used to be a standalone numbered script; those have since been
consolidated into the package structure described in `README.md`. Nothing
described here is hypothetical — every stage was actually run (see
`docs/DEMO_SCRIPT.md` for the real numbers this history produced).

## 0.1.0 — initial build (numbered prototype scripts)

1. **Attach point confirmed.** A minimal LangGraph app with two toy agents
   and a middleware that only printed on `before_model`/`after_model`,
   to confirm the hook points fire correctly before any real detection
   logic was added.
2. **Mirroring score.** Added the core signal: cosine similarity between
   an agent's input and output embeddings, using real sentence
   embeddings (`all-MiniLM-L6-v2`), checked against one fixed global
   threshold (0.75).
3. **Canary token.** Added a second, independent signal: a random
   per-call token injected into the system prompt, flagged if it
   reappears in the output. Switched from separate `before_model`/
   `after_model` hooks to a single `wrap_model_call` hook, since both
   the request and the response are needed together.
4. **Antibody store.** Added the shared, cross-agent memory: once one
   agent confirms a threat, every other agent checks new input against
   that memory first, before calling its model at all.
5. **Quarantine + audit log.** Added agent-level quarantine (pausing a
   confirmed-compromised agent entirely, not just blocking one message)
   and a structured, exportable `.jsonl` audit log.
6. **Live dashboard.** Added a FastAPI + WebSocket dashboard visualizing
   the mesh in real time.
7. **Benign corpus run — the honest finding.** Ran the fixed
   global-threshold detector (from step 2) against eight realistic
   benign tasks. Found real false positives: legitimate proofreading
   (0.902) and instruction-confirmation (0.920) scored *higher* than the
   one confirmed real attack recorded in this project's audit log
   (0.549 — see `logs/example_audit_log.jsonl`). A single global
   threshold cannot separate these categories — this is the actual
   limitation, not a hypothetical one. (A later re-run of the same
   corpus also flagged a third case — an off-topic summarization task,
   0.804 — confirming this isn't a one-off artifact of the first run.)
8. **Per-agent baseline fix.** Replaced the flat global threshold with a
   per-agent adaptive baseline: each agent's mirroring score is judged
   against its *own* rolling history once it has enough samples, instead
   of one number for every agent. Found and fixed a real bootstrap
   deadlock in the process: the first version of this gated "is this
   safe to learn from" on the same threshold it was replacing, so an
   agent whose true normal sits above that threshold could never
   accumulate history to graduate out of cold start. Fixed by decoupling
   learning (gated only by canary detection) from blocking (gated by a
   warmed-up baseline).

## 0.2.0 — consolidation into a proper repo

- Retired the numbered `stepN_*.py` prototype scripts. Their logic was
  split into a real package (`immunemesh/signals`, `immunemesh/control_plane`,
  `immunemesh/actuator`, `immunemesh/middleware`, `immunemesh/testing`) with
  runnable entry points under `demo/` and `benchmarks/`.
- **The step 8 baseline fix is no longer a separate script or an
  "alternate" code path.** `immunemesh/signals/baseline.py` and
  `immunemesh/middleware/langgraph_hooks.py` implement the corrected,
  per-agent-baseline behavior natively — there is no flat-threshold
  version shipped alongside it in production code. The flat-threshold
  approach is preserved only as "Part 1" of
  `benchmarks/benign_corpus_eval.py`, specifically to demonstrate the
  problem it had, side by side with the fix.
- Renamed prototype identifiers to their production names throughout
  (e.g. `Agent-1 (email assistant)` style ad hoc IDs standardized to
  `agent-1-email-assistant`; module names moved from `stepN_*` to
  `signals/`, `control_plane/`, `actuator/`, `middleware/`).
- Deduplicated the `LeakySystemPromptModel`, `cosine_similarity`, and
  text-extraction helpers that were previously copy-pasted into every
  step script into single shared modules.
