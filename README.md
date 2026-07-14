# ImmuneMesh — Runtime Behavioral Immune System for Multi-Agent AI

ImmuneMesh is a LangGraph middleware framework that transforms raw agent-to-agent
messages into a shared, mesh-wide threat memory. Instead of scanning a single
message in isolation, ImmuneMesh watches what agents *do* to each other's
messages at runtime — so once one agent is fooled, the rest aren't.

ImmuneMesh serves as both a runtime guardrail for production agent meshes and
an educational platform for learning AI security concepts. Built specifically
against the Morris-II class of threat — self-replicating prompt injection —
it's suitable for individual researchers, AI security teams, and students
developing agentic-security skills.

## ImmuneMesh Key Capabilities

### 🎓 Learn AI Security Methodologies
- Master cross-agent propagation detection and mesh-wide behavioral memory
- Understand mirroring-score analysis and canary-token detection
- Study self-replicating prompt injection (Morris-II class) attack patterns
- Learn per-agent adaptive baselines vs. flat global thresholds

### 🔬 Practice and Research Detection Logic
- Experiment with detection signals across a full 3-agent simulated mesh
- Develop and test false-positive tuning against a benign task corpus
- Research the exact bootstrap-deadlock bug this project found and fixed
- Study honest, documented limitations instead of a polished-only demo

### 🛡️ Run Investigations
- Watch a live 3-agent mesh get attacked and contained via a real-time dashboard
- Trace the full "Immune Signal" audit trail for any run, exportable as `.jsonl`
- Quarantine a compromised agent entirely, not just block one bad message
- Evaluate mirroring-score false positives against your own task categories

### ⚡ Platform Capabilities
- **2 independent detection signals** — mirroring score + canary token
- **Shared antibody store** — one agent's detection protects the whole mesh
- **Agent-level quarantine** — pauses a confirmed-compromised agent entirely
- **Per-agent adaptive baseline** — replaces one global threshold with learned, agent-specific normal ranges
- **Structured audit log** — SIEM-ready `.jsonl` output
- **Live dashboard** — FastAPI + WebSocket, real-time mesh visualization

Whether you're learning AI security, researching cross-agent propagation,
developing detection logic, or evaluating false-positive rates on your own
agent mesh, ImmuneMesh provides a comprehensive sandbox to explore and test.

---

## Requirements

- Python 3.10 or later
- `pip` and (recommended) a virtual environment tool
- Normal internet access on first run — downloads a small (~90MB)
  `all-MiniLM-L6-v2` embedding model from Hugging Face automatically, once
- No GPU required; runs on CPU
- No real LLM provider API key needed — every script uses fake/local models
  by design (see "Responsible use" below)

---

## Installation

### Download the Repository

**Option A: Using Git**
```bash
git clone https://github.com/nithiya-rajesh/immunemesh.git
cd immunemesh
```

**Option B: Direct Download**
1. Download ZIP from the GitHub repository
2. Extract to a folder (e.g. `C:\immunemesh` or `~/immunemesh`)

### Install ImmuneMesh

```bash
python3 -m venv immunemesh-env
source immunemesh-env/bin/activate      # Windows: immunemesh-env\Scripts\activate

pip install -r requirements.txt
pip install -e .                        # makes `import immunemesh` work from demo/ and benchmarks/
```

**Verify installation:**
```bash
python -c "import immunemesh; print(immunemesh.__version__)"
```
Expected output: `0.2.0`

If you see `ModuleNotFoundError: No module named 'immunemesh'`, the
`pip install -e .` step above was skipped or run in the wrong environment —
re-run it from the folder containing `pyproject.toml`.

---

## Getting Started

### Your First Run

Start with the console demo — a 3-agent mesh gets attacked, contained, and
logged:

```bash
python demo/simulated_mesh.py
```

**Expected result:** four verdicts printed in sequence —
`confirmed_malicious` → `blocked_agent_quarantined` → `blocked_antibody_match`
→ `clean` — followed by a summary and a written audit log at
`logs/immunemesh_audit_log.jsonl`.

- **No verdicts printed / import errors:** see Troubleshooting below.
- **First run is slow:** the embedding model is downloading (~90MB, one-time).

### Command Discovery

```bash
# See what's actually installed
python -c "import immunemesh; print(immunemesh.__file__)"

# Explore each module's docstring
python -c "import immunemesh.signals.baseline; help(immunemesh.signals.baseline)"
```

---

## Module Reference

| ImmuneMesh Module | What it does | Location |
|---|---|---|
| Mirroring score | Cosine similarity between an agent's input and output embeddings | `immunemesh/signals/embeddings.py` |
| Canary token | Detects prompt/system-message leakage via a secret per-call marker | `immunemesh/signals/canary.py` |
| Per-agent baseline | Adaptive mirroring threshold, replacing one flat global number | `immunemesh/signals/baseline.py` |
| Antibody store | Shared, mesh-wide memory of confirmed threat patterns | `immunemesh/control_plane/antibody_store.py` |
| Quarantine manager | Pauses a confirmed-compromised agent entirely | `immunemesh/actuator/quarantine.py` |
| Audit log | Structured, exportable `.jsonl` signal trail | `immunemesh/actuator/audit_log.py` |
| Middleware | The single LangGraph attach point tying everything together | `immunemesh/middleware/langgraph_hooks.py` |

---

## Command Examples

### Console 3-agent demo
```bash
# Full mesh run: attack, containment, clean pass-through, audit log
python demo/simulated_mesh.py
```

### Live dashboard
```bash
uvicorn demo.dashboard:app --reload
# open http://127.0.0.1:8000 in a browser, click "Run Demo"

# or run it directly without the uvicorn CLI:
python demo/dashboard.py
```

### False-positive benchmark
```bash
# Flat global threshold vs. the corrected per-agent baseline, side by side
python benchmarks/benign_corpus_eval.py
```

### What the live dashboard looks like

<img width="1352" height="692" alt="dashboard" src="https://github.com/user-attachments/assets/3c4d542a-634b-4cac-9a95-ee150695c663" />

Agent 1 gets hit with a Morris-II style payload and is confirmed malicious
(canary echo detected, antibody created). Agent 2 receives the identical
payload and is pre-emptively blocked — the model is never even called,
because the antibody from Agent 1 already caught it. Agent 3 gets an
unrelated benign message and passes through clean. This is a real run, not
a mockup — see `logs/example_audit_log.jsonl` for the matching structured
audit trail.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'immunemesh'`
The package itself isn't installed in your active environment.
```bash
cd immunemesh   # the folder containing pyproject.toml
pip install -e .
```

### `FileNotFoundError` when saving the audit log
Fixed in the current version — `AuditLog.save()` now creates the `logs/`
directory automatically if it doesn't exist, and the demo scripts resolve
the path relative to the project root regardless of your current directory.

### `Warning: You are sending unauthenticated requests to the HF Hub`
Harmless. Set `HF_TOKEN` as an environment variable for higher rate limits,
or ignore it — the model still downloads and caches normally.

### Installing `torch` / `sentence-transformers` runs out of disk space
The default PyPI `torch` wheel on Linux/Windows pulls in the full CUDA
toolkit as dependencies (several GB) even if you don't have a GPU. If disk
space is tight, install the CPU-only build instead:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Dashboard runs but nothing happens in the browser
Make sure you're running it via `uvicorn demo.dashboard:app --reload` (or
`python demo/dashboard.py`, which now also works) — not by importing the
file some other way. Then open `http://127.0.0.1:8000` and click **Run Demo**.

---

## Frequently Asked Questions

**Q: What if my demo run shows different mirroring scores than the docs?**
A: Scores can vary slightly by embedding model version/hardware. What
matters is the *pattern* — which categories false-positive and whether the
per-agent baseline fixes them — not bit-for-bit reproduction of one run's
numbers.

**Q: Does this replace input filtering, output moderation, or tool sandboxing?**
A: No. ImmuneMesh is one additional layer, specifically for cross-agent
propagation — it's designed to sit alongside those, not replace them.

**Q: Can I use this against a real production agent mesh?**
A: Not as-is. This is a sandboxed research prototype — synthetic data and
fake/local models throughout, not adversarially hardened, and only tested
by its own author. See "Known limitations" below before considering any
production use.

**Q: Why does the per-agent baseline need a "cold start" period?**
A: A brand-new agent has no history to judge "normal" against yet, so it
falls back to a global threshold in an advisory-only capacity until it has
enough samples — see `immunemesh/signals/baseline.py` for the full reasoning.

---

## Known Limitations — Stated Honestly, On Purpose

**Mirroring score alone cannot separate all attacks from all benign tasks.**
Real testing found legitimate proofreading and instruction-confirmation
tasks scoring *higher* than a confirmed real attack. The per-agent baseline
resolves this for tasks that are consistently high- or low-mirroring by
nature, but doesn't make the underlying signal perfect — it makes the
*threshold* smarter, not the signal itself flawless.

**Baseline poisoning is a real, unresolved risk.** Because the baseline
learns from an agent's own recent history, a patient attacker could try to
gradually shift what "normal" looks like for an agent before striking. This
is mitigated partially (canary detection is never subject to baseline
adaptation, and history has a bounded size so old data ages out) but the
general problem of detecting slow, deliberate baseline drift is unsolved.

**This has only been tested in a sandbox**, against synthetic attacks and a
small (8-case) benign corpus. It has not been tested against real
production traffic, adversarially red-teamed by anyone other than its own
author, or tested against attack variants deliberately designed to evade
the exact signals used here.

---

## Responsible Use

- Everything here should stay tested against your own sandbox, synthetic
  data, and local/fake models — unauthorized access law, data protection
  law, and third-party API terms of service all point the same direction.
- The attack simulations in this project (`LeakySystemPromptModel`, canned
  malicious payloads) are intentionally toy-scale and only functional
  against the fake models defined in this same project — not a
  general-purpose attack tool.

---

## Support & Resources

**Getting Help**
- Issues: report bugs or request features on GitHub Issues
- Documentation: `docs/architecture.md` for full system design, `docs/DEMO_SCRIPT.md` for a guided walkthrough
- Module docstrings: every file under `immunemesh/` documents its own design decisions inline

## Contributing

Contributions are welcome — feel free to submit pull requests, report bugs,
or suggest enhancements.

## References

- Cohen, Bar-Gil, et al., "ComPromptMized: Unleashing Zero-click Worms that
  Target GenAI-Powered Applications" (the Morris-II research this project's
  threat model is built around)
- NATO's Autonomous Intelligent Cyber-defense Agent (AICA) research group
- LangChain / LangGraph middleware documentation (`before_model`,
  `after_model`, `wrap_model_call` hooks used throughout this project)

## License

MIT — see `LICENSE`.

## Copyright

© 2026 Nithiya Rajendran. All rights reserved.
