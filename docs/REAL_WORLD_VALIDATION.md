# Real public winner-artifact validation

Validated 2026-10-18 with evaluator v0.2.0. [Machine-readable results](validation/saai-may-2026.json).

## What was actually tested

The evaluator was run on the saved public artifacts of **Saai Syvendra, May 2026 winner**. HackerRank's [own winner announcement](https://www.linkedin.com/posts/hackerrank_ai-is-changing-what-it-means-to-be-a-developer-activity-7473306333627277312-lhfZ) corroborates the placing. The public snapshot is pinned to [fadb4f24e36d860a9ce4d5155bb30568df80ea4b](https://github.com/saai-syvendra/hackerrank-orchestrate/tree/fadb4f24e36d860a9ce4d5155bb30568df80ea4b). Its precise identity with the original submitted competition ZIP/run is not established.

- The actual saved [output.csv](https://github.com/saai-syvendra/hackerrank-orchestrate/blob/fadb4f24e36d860a9ce4d5155bb30568df80ea4b/support_tickets/output.csv): 29 prediction rows for 29 input tickets
- All 29 tracked files under code/, including 27 Python files, checked against their pinned Git blob hashes before static analysis
- A source-only ZIP reconstructed locally from those files; this is not the original submitted archive
- No authentic coding-tool transcript was present, so transcript authenticity/quality remain unknown

The problem statement, input tickets and labelled sample are byte-identical to the files in the pinned [official May repository, b5a301c9e89d2f05cf4a7b04136a1399b6f3f0f4](https://github.com/interviewstreet/hackerrank-orchestrate-may26/tree/b5a301c9e89d2f05cf4a7b04136a1399b6f3f0f4). Full SHA-256 digests are recorded in the JSON report. No repository-root LICENSE was found for the candidate at this pin; raw third-party source, tickets and predictions are not redistributed in this evaluator.

## Results and what they mean

- All 29 saved predictions pass the May structural checks: required fields, row count, input correspondence, status/request-type enums and nonempty response/justification
- Thirteen rows differ byte-for-byte in echoed input whitespace. The documented May check collapses Unicode whitespace for identity matching; it does not rewrite words, case or answer labels. All 29 then align in original row order
- Saved statuses are 15 replied / 14 escalated; request types are 22 product_issue / 4 bug / 3 invalid. These are distributions, not accuracy metrics
- All 27 Python files parse. README and dependency declarations are present; tests/lockfile presence proxies are absent. These proxies do not grade the winner's engineering quality
- The reconstructed source-only ZIP passes the local ZIP safety/hygiene policy
- The ordinary baseline evaluation exits **2/incomplete**, correctly retaining semantic and transcript unknowns. `validate-public` exits **0** when the calibration expectations themselves hold; that is not an agent pass or official score

The actual 29 prediction tickets have **zero input-key overlap with the 10 labelled sample tickets**. Comparing the first ten output rows to those sample labels would score unrelated tickets. This validation therefore reports accuracy and official score as null. It never treats the winner's predictions as gold answers.

## Detection controls on copies of the real output

Nine synthetic corruptions are caught: missing row, extra duplicate row, same-count duplicated ticket, swapped rows, altered echoed issue, invalid status, blank response, blank justification and missing request_type column.

Three controls deliberately stay unknown:

- Flip every status between its two valid values: the schema still passes, routing correctness stays unknown
- Insert a syntactically valid invented response: the schema still passes, factual grounding stays unknown
- Remove optional input echoes while retaining required output fields: row count passes, input correspondence stays unknown

All controls operate on temporary local copies. They are synthetic perturbations, never claimed to be the winner's predictions or new expected labels. The committed JSON contains aggregate findings and digests, not copied ticket/response text.

## Reproduce it

From this evaluator checkout, with Python 3.10+ and Git installed:

```sh
git clone https://github.com/saai-syvendra/hackerrank-orchestrate.git ../orchestrate-public-may-winner
git -C ../orchestrate-public-may-winner checkout --detach fadb4f24e36d860a9ce4d5155bb30568df80ea4b
git clone https://github.com/interviewstreet/hackerrank-orchestrate-may26.git ../orchestrate-official-may
git -C ../orchestrate-official-may checkout --detach b5a301c9e89d2f05cf4a7b04136a1399b6f3f0f4
python -m orchestrate_eval validate-public --candidate-dir ../orchestrate-public-may-winner --official-dir ../orchestrate-official-may --report-dir reports/saai-public-may
```

Cloning requires network; calibration runs on those local full clones. Don't install candidate requirements or run its entry point. The command verifies commit pins, official input/spec identities, every tracked code-file blob and absence of extra source paths. It then invokes only this evaluator's static/data checks and Git object reads. Changed snapshots are refused. Open reports/saai-public-may/validation.html and baseline/report.html.

## Boundaries and source observations

This is genuine saved-artifact and static-source validation. It does **not** rerun the live agent, its tests or provider APIs; reproduce its leaderboard score; prove factual grounding; or judge its missing development transcript. Original run cost/tokens/latency/memory are unknown. This validation makes no model calls.

Inspection of the pinned [citation guard](https://github.com/saai-syvendra/hackerrank-orchestrate/blob/fadb4f24e36d860a9ce4d5155bb30568df80ea4b/code/agent/middleware/citation_guard.py) confirms implemented filtering of cited paths against read traces. It also allows a reply with a citation-mismatch flag when some read occurred but no cited paths remain. This is evidence of a guard implementation, not proof that every response is grounded. No runtime trace was supplied to verify the saved answers' reads.

The June [Swayam public repository](https://github.com/swayam-mishra/hackerrank-orchestrate/tree/fc033c4026cd8b751dd121cf7dbce8925d18e58c/hackerrank-orchestrate-june) was also inspected. Its README explicitly identifies the current data as tiny made-up demos and the source as cleaned up; saved June predictions are absent. It was not used as genuine output calibration.

This exercise exposed a real coverage gap: v0.1 had no May checker and would correctly report that task as unsupported/unknown. v0.2 adds the published May structural contract, the explicit whitespace identity policy, twelve calibration controls and reproducible provenance checks. It still does not pretend to reproduce the hidden judge.
