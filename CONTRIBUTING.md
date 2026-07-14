# Contributing to ImmuneMesh

Thank you for your interest in contributing to ImmuneMesh — a research
prototype exploring runtime, mesh-wide behavioral memory for multi-agent
AI systems.

## Before you start

This is an early-stage research project, not a production security tool.
Contributions that strengthen the honest-limitations framing (better
tests, more realistic benign/attack corpora, clearer documentation of
what's *not* solved) are just as valuable as new detection features.

## Types of contributions welcome

- **Bug fixes** in the detection logic, middleware, or demos
- **New or improved detection signals** (beyond mirroring score + canary)
- **Benchmark expansion** — more realistic benign task categories in
  `benchmarks/benign_corpus_eval.py`, or a larger/more adversarial attack corpus
- **Documentation improvements** — clearer setup steps, more accurate
  numbers, better explanations of the honest limitations
- **Test coverage** — this project doesn't yet have a formal test suite;
  adding one (pytest, with a stubbed embedding model so tests don't need
  network access) would be a high-value contribution
- **Platform/dependency fixes** — e.g. Windows-specific path issues,
  lighter-weight embedding model options

## Development process

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `main` (e.g. `git checkout -b fix/audit-log-path`)
3. Set up your environment:
```bash
   python3 -m venv immunemesh-env
   source immunemesh-env/bin/activate      # Windows: immunemesh-env\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
```
4. **Make your changes**, and run the existing demos/benchmarks to confirm
   nothing broke:
```bash
   python demo/simulated_mesh.py
   python benchmarks/benign_corpus_eval.py
```
5. **Write a clear commit message** describing what changed and why
6. **Submit a pull request** with a description of the change and, if
   relevant, before/after numbers (e.g. false-positive rate changes)

## Code standards

- Follow standard Python style (PEP 8); this project doesn't currently
  enforce a formatter, but consistent style with the existing code is
  appreciated
- Add or update docstrings for any new module, especially anything
  touching detection logic — this project documents *why* a design
  decision was made, not just *what* the code does (see
  `immunemesh/signals/baseline.py` for the style to match)
- If you change detection thresholds or add a new signal, include the
  reasoning and any test data that justifies it — numbers without
  justification won't be merged as-is
- Don't remove or soften the "Known limitations" sections in `README.md`
  or `docs/` without discussion — the honest framing is a deliberate
  design choice, not an oversight

## Pull request process

1. Describe your changes clearly in the PR description
2. Reference any related issues with `#issue-number`
3. Be responsive to feedback during review
4. Update `CHANGELOG.md` if your change is user-visible

## Reporting bugs or requesting features

Open an issue on GitHub. For bugs, include:
- What you ran (exact command)
- What you expected vs. what happened
- Your Python version and OS

## Security-related issues

If you find something that could be used to bypass detection in a way
that's unexpected (beyond the documented limitations), please open an
issue describing it — this project explicitly documents its limitations
rather than hiding them, so responsible disclosure here is just: open an
issue, no embargo needed, since there's no production deployment at risk.

## Licensing

ImmuneMesh is MIT licensed (see `LICENSE`). By submitting a contribution,
you agree it will be distributed under the same MIT license, and you
confirm you have the right to submit it (you own the copyright, or have
permission from your employer/copyright holder if applicable). You retain
copyright to your own contributions.

## Code of conduct

- Be respectful and professional in all interactions
- Focus on constructive feedback
- Help keep this a welcoming space for people learning AI security, not
  just experienced practitioners

Thank you for helping improve ImmuneMesh.