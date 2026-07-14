# ImmuneMesh

A runtime behavioral immune system for multi-agent AI meshes. Instead of
scanning an agent before it's installed, ImmuneMesh watches what agents
actually *do* to each other's messages at runtime — and gives the mesh a
shared memory, so once one agent is fooled, the rest aren't.

Built specifically against the Morris-II class of threat: self-replicating
prompt injection, where a compromised agent mirrors a malicious input back
into its own output, and any downstream agent that consumes that output
gets infected the same way. No file dropped, no code executed — the
propagation mechanism is the conversation itself.

## What this is (and isn't)

ImmuneMesh defends the **AI-agent-to-agent conversation layer**. It does
not cover raw network intrusion detection, traditional web app security, or
IoT/sensor hardening. It's also not a replacement for existing
defense-in-depth layers (input filtering, output moderation, tool
sandboxing, audit logging) — it's the one layer those don't cover: **is
the same payload propagating across multiple agents right now, and has any
agent already learned to recognize it.**

See `docs/architecture.md` for the full design and `CHANGELOG.md` for how
this was actually built, in order.

## Repo layout

```
immunemesh/
├── immunemesh/                # the installable package
│   ├── signals/
│   │   ├── embeddings.py      # shared embedding model + cosine similarity
│   │   ├── canary.py          # canary-token signal
│   │   └── baseline.py        # per-agent adaptive mirroring baseline (the fix — see CHANGELOG.md)
│   ├── control_plane/
│   │   └── antibody_store.py  # shared cross-agent threat memory ("lymph node")
│   ├── actuator/
│   │   ├── quarantine.py      # agent-level quarantine
│   │   └── audit_log.py       # structured, exportable audit log
│   ├── middleware/
│   │   └── langgraph_hooks.py # ImmuneMeshMiddleware — the single attach point
│   └── testing/
│       └── fakes.py           # shared fake/demo-only models
├── demo/
│   ├── simulated_mesh.py      # console 3-agent demo
│   └── dashboard.py           # live FastAPI + WebSocket dashboard
├── benchmarks/
│   └── benign_corpus_eval.py  # false-positive check: flat threshold vs. per-agent baseline
├── docs/
│   ├── architecture.md        # full system design
│   └── DEMO_SCRIPT.md         # presentation script with real numbers
├── logs/                      # audit log output lands here
├── CHANGELOG.md                # how this was actually built, in order
├── requirements.txt
└── LICENSE
```

## Setup

```bash
python3 -m venv immunemesh-env
source immunemesh-env/bin/activate      # Windows: immunemesh-env\Scripts\activate
pip install -r requirements.txt
pip install -e .                        # makes `immunemesh` importable from demo/ and benchmarks/
```

First run of any script using the embedding model will download a small
(~90MB) model from Hugging Face automatically — normal internet access
required, only happens once, cached afterward.

**Sandbox principle followed throughout this project:** every script here
uses fake/local models (`FakeListChatModel`, a custom `LeakySystemPromptModel`
in `immunemesh/testing/fakes.py`) and synthetic, made-up test data. Nothing
here talks to a real LLM provider API or touches real personal/company
data — see "Responsible use" below for why that matters.

## Running it

```bash
# 3-agent console demo (writes logs/immunemesh_audit_log.jsonl)
python demo/simulated_mesh.py

# live dashboard
uvicorn demo.dashboard:app --reload
# open http://127.0.0.1:8000, click "Run Demo"

# false-positive check (flat threshold vs. the per-agent baseline fix)
python benchmarks/benign_corpus_eval.py
```

### What the live dashboard looks like

![ImmuneMesh live dashboard — Agent 1 infected (red), Agent 2 blocked (orange), Agent 3 clean (green), with the signal log below](docs/screenshots/dashboard.png)

Agent 1 gets hit with a Morris-II style payload and is confirmed malicious
(canary echo detected, antibody created). Agent 2 receives the identical
payload and is pre-emptively blocked — the model is never even called,
because the antibody from Agent 1 already caught it. Agent 3 gets an
unrelated benign message and passes through clean. This is a real run,
not a mockup — see `logs/example_audit_log.jsonl` for the matching
structured audit trail.

## Known limitations — stated honestly, on purpose

**Mirroring score alone cannot separate all attacks from all benign tasks.**
Real testing found legitimate proofreading and instruction-confirmation
tasks scoring *higher* than some real attacks. The per-agent baseline
resolves this for tasks that are consistently high- or low-mirroring by
nature, but doesn't make the underlying signal perfect — it makes the
*threshold* smarter, not the signal itself flawless.

**Baseline poisoning is a real, unresolved risk.** Because the baseline
learns from an agent's own recent history, a patient attacker could try to
gradually shift what "normal" looks like for an agent before striking.
This is mitigated partially (canary detection is never subject to baseline
adaptation, and history has a bounded size so old data ages out) but the
general problem of detecting slow, deliberate baseline drift is unsolved.

**This has only been tested in a sandbox**, against synthetic attacks and
a small (8-case) benign corpus. It has not been tested against real
production traffic, adversarially red-teamed by anyone other than its own
author, or tested against attack variants deliberately designed to evade
the exact signals used here.

## Responsible use

- Everything here should stay tested against your own sandbox, synthetic
  data, and local/fake models — unauthorized access law, data protection
  law, and third-party API terms of service all point the same direction.
- The attack simulations in this project (`LeakySystemPromptModel`, canned
  malicious payloads) are intentionally toy-scale and only functional
  against the fake models defined in this same project — not a
  general-purpose attack tool.

## References

- Cohen, Bar-Gil, et al., "ComPromptMized: Unleashing Zero-click Worms that
  Target GenAI-Powered Applications" (the Morris II research this
  project's threat model is built around)
- NATO's Autonomous Intelligent Cyber-defense Agent (AICA) research group
- LangChain / LangGraph middleware documentation (`before_model`,
  `after_model`, `wrap_model_call` hooks used throughout this project)

## License

MIT — see `LICENSE`.
