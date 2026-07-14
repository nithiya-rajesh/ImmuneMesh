# LinkedIn post — ImmuneMesh

## Option A (full version)

Most AI guardrail frameworks check one agent, one message, at one point in
time. None of them ask: is this same payload echoing across three different
agents in my system right now?

That gap is exactly what self-replicating prompt injection (the "Morris-II"
class of attack) exploits — an agent gets tricked into mirroring a malicious
input back into its own output, and every downstream agent that reads that
output gets infected the same way. No malware, no exploit — the
conversation itself is the propagation mechanism.

I built ImmuneMesh, a small research prototype, to test one idea: give a
multi-agent mesh a shared memory, the way biological immunity works, so
once one agent is fooled, the rest aren't.

It runs as LangGraph middleware and combines two independent signals —
a mirroring score (how similar an agent's output is to its input) and a
canary token (a secret marker that should never echo back) — with a
shared "antibody store": once one agent confirms a threat, every other
agent blocks the same payload before its model is even called.

The part I'm actually proud of isn't the attack demo — it's what I found
when I tried to break my own detector. Testing it against 8 realistic
benign tasks (summarization, translation, proofreading) found real false
positives: legitimate proofreading scored *higher* on my mirroring signal
than a confirmed real attack. One global threshold couldn't tell them
apart. Fixing that exposed a genuine bootstrap deadlock bug along the way,
which was a good reminder that testing against real data beats testing
against assumptions.

This is a sandboxed research prototype, not a production tool — synthetic
data and local/fake models throughout, on purpose, and it's explicitly not
adversarially hardened. But the core idea — mesh-wide behavioral memory as
a missing layer in agent security — seems worth sharing.

Repo (with the honest limitations documented, not buried):
[your GitHub link here]

#AIsecurity #MultiAgentSystems #LangGraph #PromptInjection #AISafety

---

## Option B (shorter version)

Every current AI guardrail checks one agent, one message, at a time. None
of them ask whether the same malicious payload is spreading across
multiple agents right now — which is exactly the mechanism
self-replicating prompt injection (Morris-II class attacks) relies on.

I built ImmuneMesh to test a different approach: give a multi-agent mesh
shared memory, so once one agent is fooled, the rest aren't blocked. It
runs as LangGraph middleware, combining a mirroring-score signal with a
canary-token check and a shared "antibody store" that lets one agent's
detection pre-emptively protect every other agent in the mesh.

The most useful part of building it was finding where it breaks: testing
against realistic benign tasks turned up real false positives (legitimate
proofreading scored higher than a confirmed attack on one signal alone),
which led to a per-agent adaptive baseline fix — and a genuine bootstrap
bug along the way.

Research prototype, sandboxed by design, limitations documented openly.
Repo: [your GitHub link here]

#AIsecurity #AgenticAI #PromptInjection
