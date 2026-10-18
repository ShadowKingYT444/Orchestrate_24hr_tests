# Actual source/output quality judging of the public May winner

The earlier structural report was insufficient for quality grading. v0.3 adds an independent evidence-backed numerical review of the actual public agent source and saved answers, alongside the new executed benchmark/judge pipeline.

Candidate: Saai Syvendra's public May-winner repository at fadb4f24e36d860a9ce4d5155bb30568df80ea4b. Input/spec identities and saved-output hashes remain verified in REAL_WORLD_VALIDATION.md. No leaderboard score was used to tune these estimates.

## Local category estimates

- Code: 17.8125/30
- Output: 26.0819/30
- Coding transcript: unknown, no genuine export available
- Known subtotal: 43.8944/60
- Missing-transcript interval: 43.8944–53.8944/70

These are uncalibrated local model/human-style judgments, not recovered official grades or an accuracy claim. The output judgment has a qualitative sensitivity range of 21–27/30; this is not a statistical confidence interval. These saved May tasks differ from the authored support-world benchmark, so its numbers must not be used to rank the winner against our toy agents.

## Evidence and method

All 27 Python files were read for code quality, using the historical May architecture/prompt-tool/robustness/rigor dimensions. Ratings were 75/62.5/50/37.5 on 0–100 and combined with the 30/30/25/15 subweights, then the 30-point category weight. Implemented strengths and source-derived risks were separated from untested runtime behavior. Exact limited source quotes and line ranges were verified against the exported source bundle; no raw source bundle is redistributed.

[Code rubric review](validation/saai-code-rubric-review.json).

All 29 saved answers were reviewed against the original task and supplied support corpus for routing, product/type classification, response meaning, factual support and justification consistency. The output review uses explicit LOCAL field weights 25/10/10/35/20, not a claimed official formula. It records per-row ratings, paraphrased rationale, primary corpus links/digests, uncertainty and safety/justification limitations.

[Output semantic review](validation/saai-output-semantic-review.json). [Category summary](validation/saai-ranking-estimates.json).

There are no independent exact labels for those 29 tickets: the 10 labelled sample inputs are disjoint. Therefore the numerical output result is a corpus-grounded quality estimate, not exact-gold accuracy. This is source/saved-output judging; the live winner agent and its tests were not executed, and provider costs/tokens/runtime were not invented. Transcript absence stays unknown, never zero.

## Executed benchmark calibration

The own-code reference agent and deliberately unsafe agent were actually executed on the same 20 authored, reference-backed cases. Their real responses and justifications were independently judged, including failures and Spanish tickets. Code was also rated with source evidence:

- Competent: code 21.375/30, output 26.5575/30, known 47.9325/60
- Unsafe:code4.5/30, output 5.25/30, known9.75/60

The competent agent lost points for generic justifications claiming evidence use on unavailable-evidence cases and for answering Spanish tickets in English. The unsafe baseline invented policies and claimed access restoration without tools; whole-case safety caps apply. No authentic coding transcripts exist for these demonstration scripts, so none were fabricated.

Preserved actual runs, source/evidence bundles and independent reviews are in benchmarks/results/. Reproduce their arithmetic and verified imports offline with python examples/replay_benchmark_scores.py. This replays saved real runs; use benchmark run for fresh execution and a fresh judge bundle/review. Old reviews cannot silently grade changed execution evidence.
